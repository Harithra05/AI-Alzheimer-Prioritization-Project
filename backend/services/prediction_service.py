from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd

from backend.services.quality_service import calculate_quality


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "artifacts" / "stage1_model.joblib"


class PredictionService:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Stage-1 model not found: {MODEL_PATH}"
            )

        # The saved artifact is a dictionary containing
        # the preprocessing/model pipeline and calibration object.
        artifact = joblib.load(MODEL_PATH)

        self.stage = artifact["stage"]
        self.pipeline = artifact["pipeline"]
        self.calibrator = artifact["calibrator"]

        self.features = artifact["features"]
        self.numeric_features = artifact["numeric_features"]
        self.categorical_features = artifact["categorical_features"]

        self.high_threshold = artifact["priority_thresholds"]["high_threshold"]
        self.medium_threshold = artifact["priority_thresholds"]["medium_threshold"]

        self.model_name = artifact["selected_model"]
        self.model_version = "stage1-logreg-v1"

    def _priority(self, risk_score: float) -> str:
        if risk_score >= self.high_threshold:
            return "HIGH"

        if risk_score >= self.medium_threshold:
            return "MEDIUM"

        return "LOW"

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:

        row = {
            feature: features.get(feature)
            for feature in self.features
        }

        df = pd.DataFrame([row])

        # First run the saved preprocessing/model pipeline.
        raw_score = self.pipeline.predict_proba(df)[:, 1]

        # Then apply the saved calibration model.
        probability = float(
            self.calibrator.transform(raw_score)[0]
        )

        quality = calculate_quality(features)

        return {
            "risk_score": probability,
            "priority": self._priority(probability),
            "data_quality": quality,
            "stage": self.stage,
            "model_version": self.model_version,
        }


prediction_service = PredictionService()