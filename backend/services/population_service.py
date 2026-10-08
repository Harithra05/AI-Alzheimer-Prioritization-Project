from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = PROJECT_ROOT / "reports" / "prioritized_cohort.csv"


def get_population_risk_distribution() -> dict:
    if not COHORT_PATH.exists():
        raise FileNotFoundError(
            f"Population cohort file not found: {COHORT_PATH}"
        )

    df = pd.read_csv(COHORT_PATH)

    risk = pd.to_numeric(
        df["risk_score"],
        errors="coerce",
    ).dropna()

    return {
        "total_patients": int(len(df)),
        "risk_scores": [
            round(float(value), 6)
            for value in risk.tolist()
        ],
        "scope": (
            "Retrospective ADNI research cohort; "
            "risk distribution is for research analysis only."
        ),
    }