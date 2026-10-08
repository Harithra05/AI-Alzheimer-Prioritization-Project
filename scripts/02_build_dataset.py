import argparse
from pathlib import Path
import pandas as pd
import numpy as np

from common import (
    load_config,
    processed_dir,
    read_prefix,
    ensure_rid,
    baseline_only,
    find_column,
)


# ============================================================
# VERIFIED ADNI VARIABLE NAMES
# ============================================================

ALIASES = {
    # Not currently confirmed in your PTDEMOG download.
    "age": ["AGE", "PTAGE", "Age"],

    "sex": [
        "PTGENDER",
        "SEX",
        "GENDER",
        "Sex",
    ],

    "education": [
        "PTEDUCAT",
        "EDUCATION",
        "YEARS_EDUCATION",
        "Education",
    ],

    # SES is not confirmed in the downloaded PTDEMOG file.
    "ses": [
        "PTSES",
        "SES",
        "SOCIOECONOMIC_STATUS",
        "Socioeconomic Status",
    ],

    # Verified ADNI fields
    "mmse": [
        "MMSCORE",
        "MMSE",
        "MMSE_TOTAL",
        "MMSE Score",
    ],

    "moca": [
        "MOCA",
        "MOCATOTS",
        "MOCA_TOTAL",
        "MoCA",
    ],

    # IMPORTANT:
    # TOTSCORE = ADAS 11 total (0-70)
    # TOTAL13 = ADAS 13 total (0-85)
    "adas": [
        "TOTSCORE",
        "ADAS11",
        "ADAS_TOTAL",
        "ADAS_COG",
        "ADAS",
    ],

    "faq": [
        "FAQTOTAL",
        "FAQ_TOTAL",
        "FAQ",
        "FAQTOTALSCORE",
    ],

    # Stage 3 MRI variables.
    # These are aliases only; we will verify whether they
    # actually exist in the downloaded MRI table.
    "eTIV": [
        "eTIV",
        "ETIV",
        "EstimatedTotalIntracranialVolume",
    ],

    "nWBV": [
        "nWBV",
        "NWBV",
        "NormalizedWholeBrainVolume",
    ],

    "ASF": [
        "ASF",
        "AtlasScalingFactor",
    ],

    "dx": [
        "DX",
        "DXCURREN",
        "CURRENT_DIAGNOSIS",
        "Diagnosis",
        "DIAGNOSIS",
    ],
}


# ============================================================
# COLUMN HELPERS
# ============================================================

def pick(df, key, required=False):
    return find_column(
        df,
        ALIASES[key],
        required=required
    )


def get_feature(df, key):
    c = pick(df, key, required=False)

    if c is None:
        return None

    return df[c]


# ============================================================
# BASELINE DEMOGRAPHICS
# ============================================================

def prepare_static_demographics():

    df = baseline_only(
        read_prefix("PTDEMOG_")
    )

    df = ensure_rid(df)

    out = pd.DataFrame({
        "RID": df["RID"]
    })

    # Only variables actually found in the downloaded file
    for key in ["age", "sex", "education", "ses"]:

        s = get_feature(df, key)

        if s is not None:
            out[key] = s.values
        else:
            out[key] = np.nan

    return out.drop_duplicates("RID")


# ============================================================
# COGNITIVE ASSESSMENTS
# ============================================================

def prepare_cognitive():

    out = None

    files = [
        ("MMSE_", "mmse"),
        ("MOCA_", "moca"),
        ("ADAS_", "adas"),
        ("FAQ_", "faq"),
    ]

    for prefix, key in files:

        try:

            df = baseline_only(
                read_prefix(prefix)
            )

            df = ensure_rid(df)

            c = pick(
                df,
                key,
                required=False
            )

            if c is None:

                print(
                    f"{prefix}: "
                    f"variable for {key} not found; skipping."
                )

                continue

            part = df[
                ["RID", c]
            ].copy()

            part[key] = pd.to_numeric(
                part[c],
                errors="coerce"
            )

            part = part[
                ["RID", key]
            ].drop_duplicates("RID")

            if out is None:

                out = part

            else:

                out = out.merge(
                    part,
                    on="RID",
                    how="outer"
                )

        except FileNotFoundError:

            print(
                f"{prefix}: "
                f"file not found; skipping."
            )

    if out is None:

        raise RuntimeError(
            "No cognitive assessment "
            "file was available."
        )

    return out


# ============================================================
# MRI VARIABLES — STAGE 3
# ============================================================

def prepare_mri():

    sources = []

    try:

        sources.append(
            baseline_only(
                read_prefix(
                    "All_Subjects_Key_MRI_"
                )
            )
        )

    except FileNotFoundError:

        pass

    try:

        sources.append(
            baseline_only(
                read_prefix(
                    "UCSFFSX7_"
                )
            )
        )

    except FileNotFoundError:

        pass

    if not sources:

        raise RuntimeError(
            "No MRI table found."
        )

    result = None

    for df in sources:

        df = ensure_rid(df)

        part = pd.DataFrame({
            "RID": df["RID"]
        })

        found = 0

        for key in [
            "eTIV",
            "nWBV",
            "ASF"
        ]:

            c = pick(
                df,
                key,
                required=False
            )

            if c is not None:

                part[key] = pd.to_numeric(
                    df[c],
                    errors="coerce"
                )

                found += 1

        if found:

            part = part.drop_duplicates(
                "RID"
            )

            if result is None:

                result = part

            else:

                result = result.merge(
                    part,
                    on="RID",
                    how="outer"
                )

    if result is None:

        raise RuntimeError(
            "Stage 3 could not find "
            "eTIV/nWBV/ASF in the downloaded "
            "MRI tables."
        )

    return result


# ============================================================
# ADNI DIAGNOSIS MAPPING
# ============================================================

def diagnosis_binary_numeric(series):

    """
    ADNI DXSUM DIAGNOSIS mapping confirmed
    from the downloaded DXSUM file:

        1 = normal / cognitively normal
        2 = MCI
        3 = Alzheimer's dementia
        10 = other / unclear

    For progression:

        1 -> 0
        2 -> 0
        3 -> 1
        10 -> missing
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce"
    )

    result = pd.Series(
        pd.NA,
        index=series.index,
        dtype="Int64"
    )

    result.loc[numeric == 1] = 0
    result.loc[numeric == 2] = 0
    result.loc[numeric == 3] = 1

    return result


# ============================================================
# TARGET
# ============================================================

def prepare_target():

    cfg = load_config()

    mode = cfg["target"].get(
        "mode",
        "progression_24m"
    )

    raw = ensure_rid(
        read_prefix("DXSUM_")
    )

    dxcol = pick(
        raw,
        "dx",
        required=True
    )

    # --------------------------------------------------------
    # BASELINE DIAGNOSIS MODE
    # --------------------------------------------------------

    if mode == "baseline_diagnosis":

        df = baseline_only(raw)

        numeric_dx = pd.to_numeric(
            df[dxcol],
            errors="coerce"
        )

        target = pd.Series(
            pd.NA,
            index=df.index,
            dtype="Int64"
        )

        # Normal/CN and MCI -> 0
        target.loc[
            numeric_dx.isin([1, 2])
        ] = 0

        # Alzheimer's dementia -> 1
        target.loc[
            numeric_dx == 3
        ] = 1

        return pd.DataFrame({
            "RID": df["RID"],
            "target": target
        }).drop_duplicates("RID")


    # --------------------------------------------------------
    # PROSPECTIVE 24-MONTH CONVERSION MODE
    # --------------------------------------------------------

    if mode == "progression_24m":

        datecol = find_column(
            raw,
            [
                "EXAMDATE",
                "EXAMDATE2",
                "USERDATE"
            ],
            required=False
        )

        if datecol is None:

            raise RuntimeError(
                "progression_24m requires "
                "EXAMDATE."
            )

        # Convert examination date
        raw["_date"] = pd.to_datetime(
            raw[datecol],
            errors="coerce"
        )

        raw = raw.dropna(
            subset=["_date"]
        ).copy()

        raw = raw.sort_values(
            ["RID", "_date"]
        )

        # Numeric ADNI diagnosis
        raw["_diagnosis"] = pd.to_numeric(
            raw[dxcol],
            errors="coerce"
        )

        # ----------------------------------------------------
        # Determine each participant's baseline
        # ----------------------------------------------------

        baseline = (
            raw.sort_values(
                ["RID", "_date"]
            )
            .groupby("RID", as_index=False)
            .first()
        )

        baseline = baseline[
            [
                "RID",
                "_date",
                "_diagnosis"
            ]
        ].rename(
            columns={
                "_date": "baseline_date",
                "_diagnosis": "baseline_diagnosis",
            }
        )

        # Only baseline CN or MCI
        baseline = baseline[
            baseline["baseline_diagnosis"].isin(
                [1, 2]
            )
        ].copy()

        # ----------------------------------------------------
        # Merge baseline information back onto
        # every longitudinal diagnosis row
        # ----------------------------------------------------

        merged = raw.merge(
            baseline,
            on="RID",
            how="inner"
        )

        merged["months_after"] = (
            merged["_date"]
            - merged["baseline_date"]
        ).dt.days / 30.4375

        # ----------------------------------------------------
        # Require >= 24 months of actual follow-up
        # ----------------------------------------------------

        last_date = (
            raw.groupby("RID")["_date"]
            .max()
            .rename("last_date")
        )

        baseline = baseline.merge(
            last_date,
            on="RID",
            how="left"
        )

        baseline["followup_months"] = (
            baseline["last_date"]
            - baseline["baseline_date"]
        ).dt.days / 30.4375

        baseline = baseline[
            baseline["followup_months"] >= 24
        ].copy()

        # ----------------------------------------------------
        # Identify dementia conversion WITHIN first 24 months
        # ----------------------------------------------------

        events = merged[
            (merged["months_after"] > 0)
            &
            (merged["months_after"] <= 24)
            &
            (merged["_diagnosis"] == 3)
        ]

        dementia_rids = set(
            events["RID"].unique()
        )

        baseline["target"] = (
            baseline["RID"]
            .isin(dementia_rids)
            .astype(int)
        )

        # ----------------------------------------------------
        # Final target table
        # ----------------------------------------------------

        out = baseline[
            [
                "RID",
                "target"
            ]
        ].copy()

        return out.drop_duplicates(
            "RID"
        )


    raise ValueError(
        f"Unsupported target mode: {mode}"
    )


# ============================================================
# MAIN DATASET CONSTRUCTION
# ============================================================

def main(stage):

    cfg = load_config()

    processed_dir().mkdir(
        parents=True,
        exist_ok=True
    )

    print("\n====================================")
    print("BUILDING DATASET")
    print("====================================")

    print(f"Stage: {stage}")

    # --------------------------------------------------------
    # Demographics
    # --------------------------------------------------------

    print("\nLoading demographics...")

    demo = prepare_static_demographics()

    print(
        f"Demographic participants: "
        f"{demo['RID'].nunique():,}"
    )

    # --------------------------------------------------------
    # Cognitive assessments
    # --------------------------------------------------------

    print("\nLoading cognitive assessments...")

    cog = prepare_cognitive()

    print(
        f"Cognitive participants: "
        f"{cog['RID'].nunique():,}"
    )

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    print("\nBuilding target...")

    target = prepare_target()

    print(
        f"Target participants: "
        f"{target['RID'].nunique():,}"
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    data = (
        demo
        .merge(
            cog,
            on="RID",
            how="inner"
        )
        .merge(
            target,
            on="RID",
            how="inner"
        )
    )

    # --------------------------------------------------------
    # Stage 3 MRI
    # --------------------------------------------------------

    if stage == "stage3":

        print(
            "\nLoading MRI variables..."
        )

        mri = prepare_mri()

        print(
            f"MRI participants: "
            f"{mri['RID'].nunique():,}"
        )

        data = data.merge(
            mri,
            on="RID",
            how="inner"
        )

    # --------------------------------------------------------
    # Clean target
    # --------------------------------------------------------

    data = data.dropna(
        subset=["target"]
    ).copy()

    data["target"] = (
        data["target"]
        .astype(int)
    )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    numeric_columns = [
        "age",
        "education",
        "mmse",
        "moca",
        "adas",
        "faq",
        "eTIV",
        "nWBV",
        "ASF",
    ]

    for c in numeric_columns:

        if c in data.columns:

            data[c] = pd.to_numeric(
                data[c],
                errors="coerce"
            )

    # --------------------------------------------------------
    # Categorical conversion
    # --------------------------------------------------------

    for c in [
        "sex",
        "ses"
    ]:

        if c in data.columns:

            data[c] = (
                data[c]
                .astype("string")
                .str.strip()
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    out_path = (
        processed_dir()
        / f"{stage}.csv"
    )

    data.to_csv(
        out_path,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        f"\nSaved dataset:"
        f"\n{out_path}"
    )

    print(
        f"\nRows: "
        f"{len(data):,}"
    )

    print(
        f"Participants: "
        f"{data['RID'].nunique():,}"
    )

    print(
        "\nColumns:"
    )

    print(
        list(data.columns)
    )

    print(
        "\nTarget distribution:"
    )

    print(
        data["target"]
        .value_counts()
        .sort_index()
    )

    print(
        "\nTarget percentage:"
    )

    print(
        (
            data["target"]
            .value_counts(
                normalize=True
            )
            * 100
        )
        .sort_index()
        .round(2)
    )

    print(
        "\nMissingness (%):"
    )

    missingness = (
        data
        .isna()
        .mean()
        * 100
    )

    print(
        missingness
        .sort_values(
            ascending=False
        )
        .round(2)
    )

    print(
        "\n===================================="
    )

    print(
        "DATASET BUILD COMPLETE"
    )

    print(
        "====================================\n"
    )


# ============================================================
# COMMAND LINE
# ============================================================

if __name__ == "__main__":

    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--stage",
        choices=[
            "stage1",
            "stage3"
        ],
        required=True
    )

    args = ap.parse_args()

    main(args.stage)