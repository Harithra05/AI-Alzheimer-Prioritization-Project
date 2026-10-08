import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from common import ROOT, load_config, raw_dir, reports_dir, read_prefix, ensure_rid, find_column

def profile_one(name, df):
    info = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "columns_list": [str(c) for c in df.columns],
        "missing_percent": (df.isna().mean().sort_values(ascending=False).head(30) * 100).round(2).to_dict(),
    }
    try:
        rid = find_column(df, ["RID", "PTID", "Subject ID", "SubjectID"], required=False)
        info["subject_identifier"] = rid
        if rid:
            info["unique_subjects"] = int(df[rid].nunique(dropna=True))
    except Exception:
        pass
    return info

def main():
    load_config()
    reports_dir().mkdir(parents=True, exist_ok=True)
    raw = raw_dir()

    csvs = sorted(raw.glob("*.csv"))
    if not csvs:
        raise SystemExit(
            f"No CSV files found in {raw}. Unzip your ADNI files and copy the CSVs into data/raw."
        )

    summary = {}
    for p in csvs:
        try:
            df = pd.read_csv(p, low_memory=False)
            summary[p.name] = profile_one(p.name, df)
            print(f"{p.name}: {len(df):,} rows x {len(df.columns):,} columns")
        except Exception as e:
            summary[p.name] = {"error": str(e)}

    with open(reports_dir() / "profile_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    # Core feature distributions if available.
    frames = []
    for prefix, label in [
        ("PTDEMOG_", "demographics"),
        ("MMSE_", "mmse"),
        ("MOCA_", "moca"),
        ("ADAS_", "adas"),
        ("FAQ_", "faq"),
        ("All_Subjects_Key_MRI_", "key_mri"),
    ]:
        try:
            df = read_prefix(prefix)
            frames.append((label, df))
        except Exception:
            pass

    # Missingness plot across core files.
    miss_rows = []
    for label, df in frames:
        for c in df.columns:
            miss_rows.append({"dataset": label, "column": str(c), "missing_pct": float(df[c].isna().mean()*100)})
    miss = pd.DataFrame(miss_rows).sort_values("missing_pct", ascending=False).head(40)
    if not miss.empty:
        plt.figure(figsize=(12, 8))
        plt.barh(miss["column"].astype(str), miss["missing_pct"])
        plt.xlabel("Missing (%)")
        plt.title("Top missingness levels across available ADNI tables")
        plt.tight_layout()
        plt.savefig(reports_dir() / "profile_missingness.png", dpi=160)
        plt.close()

    # Numeric distributions for likely model variables.
    likely = ["AGE", "PTAGE", "PTEDUCAT", "EDUCATION", "MMSCORE", "MMSE", "MOCA", "ADAS13", "FAQTOTAL", "eTIV", "nWBV", "ASF"]
    cols_found = []
    combined = pd.DataFrame()
    for label, df in frames:
        for c in df.columns:
            if str(c).upper() in {x.upper() for x in likely}:
                vals = pd.to_numeric(df[c], errors="coerce").dropna()
                if len(vals) > 0:
                    combined[str(c)] = vals.reset_index(drop=True)
                    cols_found.append(str(c))
    if not combined.empty:
        n = len(cols_found)
        fig, axes = plt.subplots(n, 1, figsize=(10, max(3, 2.5*n)))
        if n == 1:
            axes = [axes]
        for ax, c in zip(axes, cols_found):
            ax.hist(combined[c].dropna(), bins=30)
            ax.set_title(c)
            ax.set_xlabel("Value")
            ax.set_ylabel("Count")
        plt.tight_layout()
        plt.savefig(reports_dir() / "profile_distributions.png", dpi=160)
        plt.close()

    # Diagnosis class distribution.
    try:
        dx = read_prefix("DXSUM_")
        dxcol = find_column(dx, ["DX", "DXCURREN", "CURRENT_DIAGNOSIS", "Diagnosis", "DIAGNOSIS"], required=False)
        if dxcol:
            vals = dx[dxcol].astype(str).str.strip().str.lower().value_counts().head(20)
            plt.figure(figsize=(10, 5))
            plt.bar(vals.index.astype(str), vals.values)
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("Count")
            plt.title(f"Diagnosis distribution: {dxcol}")
            plt.tight_layout()
            plt.savefig(reports_dir() / "profile_class_distribution.png", dpi=160)
            plt.close()
    except Exception as e:
        print("Diagnosis profiling skipped:", e)

    print(f"\nProfile written to {reports_dir() / 'profile_summary.json'}")
    print("Review the profile BEFORE model selection.")

if __name__ == "__main__":
    main()
