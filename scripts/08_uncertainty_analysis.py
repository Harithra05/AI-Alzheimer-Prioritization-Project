from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "stage1_model.joblib"
)

BOOTSTRAP_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "stage1_bootstrap_predictions.npz"
)

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "stage1.csv"
)


class UncertaintyService:
    """
    Research uncertainty service.

    Bootstrap uncertainty is available for participants represented
    in the retrospective Stage-1 cohort.

    It does not generate clinical confidence intervals and does not
    extrapolate bootstrap uncertainty to arbitrary new patients.
    """

    def __init__(self):

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Stage-1 model not found: {MODEL_PATH}"
            )

        if not BOOTSTRAP_PATH.exists():
            raise FileNotFoundError(
                f"Bootstrap artifact not found: "
                f"{BOOTSTRAP_PATH}"
            )

        if not DATA_PATH.exists():
            raise FileNotFoundError(
                f"Stage-1 dataset not found: "
                f"{DATA_PATH}"
            )

        model_artifact = joblib.load(
            MODEL_PATH
        )

        self.pipeline = model_artifact[
            "pipeline"
        ]

        self.model_name = model_artifact[
            "selected_model"
        ]

        bootstrap = np.load(
            BOOTSTRAP_PATH
        )

        self.bootstrap_predictions = (
            bootstrap["predictions"]
        )

        self.row_indices = (
            bootstrap["row_indices"]
        )

        self.dataset = pd.read_csv(
            DATA_PATH
        )

        self.features = [
            "education",
            "mmse",
            "adas",
            "faq",
            "sex",
        ]

        if len(self.dataset) != len(
            self.row_indices
        ):
            raise RuntimeError(
                "Bootstrap artifact and Stage-1 dataset "
                "have different numbers of rows."
            )

    def _find_matching_row(
        self,
        features: Dict[str, Any],
    ):
        """
        Find an exact Stage-1 cohort row matching the supplied
        model inputs.

        Missing values are handled explicitly.
        """

        candidate = {}

        for feature in self.features:
            value = features.get(feature)

            if value is None:
                candidate[feature] = np.nan
            else:
                candidate[feature] = value

        mask = pd.Series(
            True,
            index=self.dataset.index,
        )

        for feature in self.features:

            supplied = candidate[feature]

            if pd.isna(supplied):

                mask &= self.dataset[
                    feature
                ].isna()

            else:

                mask &= np.isclose(
                    pd.to_numeric(
                        self.dataset[
                            feature
                        ],
                        errors="coerce",
                    ),
                    float(supplied),
                    equal_nan=False,
                )

        matches = self.dataset.index[
            mask
        ].tolist()

        if not matches:
            return None

        return matches[0]

    def estimate(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:

        row_index = self._find_matching_row(
            features
        )

        if row_index is None:

            production_probability = float(
                self.pipeline.predict_proba(
                    pd.DataFrame(
                        [
                            {
                                feature: features.get(
                                    feature
                                )
                                for feature in self.features
                            }
                        ]
                    )
                )[:, 1][0]
            )

            return {
                "available": False,
                "risk_score": production_probability,
                "reason": (
                    "The submitted assessment does not "
                    "match a participant row in the "
                    "retrospective bootstrap cohort. "
                    "A patient-specific bootstrap interval "
                    "is therefore not reported."
                ),
                "method": (
                    "500 bootstrap model refits were used "
                    "for retrospective cohort uncertainty. "
                    "No extrapolation is performed for "
                    "unmatched assessments."
                ),
                "model": self.model_name,
                "interpretation": (
                    "Research uncertainty only; not a "
                    "clinical confidence interval."
                ),
            }

        bootstrap_index = int(
            np.where(
                self.row_indices == row_index
            )[0][0]
        )

        values = (
            self.bootstrap_predictions[
                :,
                bootstrap_index
            ]
        )

        lower = float(
            np.percentile(
                values,
                2.5,
            )
        )

        upper = float(
            np.percentile(
                values,
                97.5,
            )
        )

        mean_probability = float(
            np.mean(values)
        )

        median_probability = float(
            np.median(values)
        )

        standard_deviation = float(
            np.std(
                values,
                ddof=1,
            )
        )

        return {
            "available": True,
            "row_index": int(row_index),
            "risk_score": float(
                self.pipeline.predict_proba(
                    pd.DataFrame(
                        [
                            {
                                feature: features.get(
                                    feature
                                )
                                for feature in self.features
                            }
                        ]
                    )
                )[:, 1][0]
            ),
            "bootstrap_mean": mean_probability,
            "bootstrap_median": median_probability,
            "lower_95": lower,
            "upper_95": upper,
            "bootstrap_std": standard_deviation,
            "bootstrap_replicates": int(
                self.bootstrap_predictions.shape[0]
            ),
            "method": (
                "Empirical interval from 500 bootstrap "
                "model refits."
            ),
            "model": self.model_name,
            "interpretation": (
                "This interval describes empirical "
                "model-estimate uncertainty in the "
                "retrospective research cohort. It is "
                "not a clinical confidence interval and "
                "should not be interpreted as diagnostic "
                "certainty or treatment guidance."
            ),
        }


uncertainty_service = UncertaintyService()