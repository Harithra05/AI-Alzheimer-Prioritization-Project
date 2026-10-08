from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "artifacts" / "stage1_model.joblib"


FEATURE_LABELS = {
    "education": "Education",
    "mmse": "MMSE",
    "adas": "ADAS",
    "faq": "FAQ",
    "sex_1.0": "Sex: Male",
    "sex_2.0": "Sex: Female",
    "missingindicator_adas": "ADAS missingness indicator",
    "missingindicator_faq": "FAQ missingness indicator",
}


class ExplanationService:

    def __init__(self):

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Stage-1 model not found: {MODEL_PATH}"
            )

        artifact = joblib.load(MODEL_PATH)

        self.pipeline = artifact["pipeline"]
        self.features = artifact["features"]
        self.model_name = artifact["selected_model"]

        self.preprocessor = None
        self.model = None

        for name, step in self.pipeline.named_steps.items():

            if (
                hasattr(step, "transform")
                and hasattr(step, "get_feature_names_out")
            ):
                self.preprocessor = step

            if hasattr(step, "coef_"):
                self.model = step

        if self.preprocessor is None:
            raise RuntimeError(
                "Could not identify the preprocessing step "
                "in the trained pipeline."
            )

        if self.model is None:
            raise RuntimeError(
                "Could not identify the linear model "
                "in the trained pipeline."
            )

    def _humanize_feature_name(self, name: str) -> str:

        # Remove preprocessing prefixes.
        cleaned = name

        for prefix in [
            "num__",
            "cat__",
        ]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]

        # Remove numerical suffix from categorical sex features.
        cleaned = cleaned.replace(
            "sex_1.0",
            "sex_1.0",
        )

        if cleaned in FEATURE_LABELS:
            return FEATURE_LABELS[cleaned]

        # Handle names that contain the categorical prefix
        # after preprocessing.
        if cleaned.startswith("sex_1.0"):
            return "Sex: Male"

        if cleaned.startswith("sex_2.0"):
            return "Sex: Female"

        if cleaned.startswith(
            "missingindicator_adas"
        ):
            return "ADAS missingness indicator"

        if cleaned.startswith(
            "missingindicator_faq"
        ):
            return "FAQ missingness indicator"

        return cleaned

    def explain(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:

        row = {
            feature: features.get(feature)
            for feature in self.features
        }

        df = pd.DataFrame([row])

        transformed = self.preprocessor.transform(df)

        coefficients = self.model.coef_[0]

        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()

        contribution_values = (
            transformed[0] * coefficients
        )

        feature_names = (
            self.preprocessor
            .get_feature_names_out()
        )

        contributions = []

        for name, value in zip(
            feature_names,
            contribution_values,
        ):

            value = float(value)

            if value > 0:
                direction = "increases model score"

            elif value < 0:
                direction = "decreases model score"

            else:
                direction = "neutral"

            contributions.append(
                {
                    "feature": self._humanize_feature_name(
                        name
                    ),
                    "raw_feature": name,
                    "contribution": value,
                    "direction": direction,
                }
            )

        contributions.sort(
            key=lambda x: abs(
                x["contribution"]
            ),
            reverse=True,
        )

        return {
            "method": (
                "Linear model coefficient contribution"
            ),
            "model": self.model_name,
            "contributions": contributions,
            "interpretation": (
                "These contributions describe model-score influence only. "
                "They are not causal effects or independent clinical effects."
            ),
        }


explanation_service = ExplanationService()