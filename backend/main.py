from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    PatientAssessment,
    PredictionRequest,
    ExplanationRequest,
    RankingRequest,
    QualityRequest,
)
from backend.services.prediction_service import prediction_service
from backend.services.ranking_service import rank_patients
from backend.services.quality_service import calculate_quality
from backend.services.explanation_service import explanation_service
from backend.services.uncertainty_service import uncertainty_service
from backend.services.population_service import get_population_risk_distribution
from backend.database import SessionLocal
from backend.models import PatientRecord
app = FastAPI(
    title="AI Alzheimer Prioritization API",
    description=(
        "Research clinical decision-support API for "
        "prioritizing patients for further diagnostic evaluation."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SCOPE = (
    "Research clinical decision-support prototype; "
    "no diagnosis or treatment recommendation."
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "stage": prediction_service.stage,
        "model": prediction_service.model_name,
        "model_version": prediction_service.model_version,
    }


@app.get("/model-info")
def model_info() -> Dict[str, Any]:
    return {
        "stage": prediction_service.stage,
        "selected_model": prediction_service.model_name,
        "model_version": prediction_service.model_version,
        "features": prediction_service.features,
        "priority_thresholds": {
            "high_threshold": prediction_service.high_threshold,
            "medium_threshold": prediction_service.medium_threshold,
        },
        "scope": SCOPE,
    }


@app.get("/population/risk-distribution")
def population_risk_distribution() -> Dict[str, Any]:
    return get_population_risk_distribution()
@app.get("/patients")
def patients() -> Dict[str, Any]:
    db = SessionLocal()

    try:
        records = (
            db.query(PatientRecord)
            .order_by(PatientRecord.created_at.desc())
            .all()
        )

        return {
            "total_patients": len(records),
            "patients": [
                {
                    "id": record.id,
                    "assessment_id": record.assessment_id,
                    "patient_ref": record.patient_ref,
                    "education": record.education,
                    "mmse": record.mmse,
                    "adas": record.adas,
                    "faq": record.faq,
                    "sex": record.sex,
                    "moca": record.moca,
                    "risk_score": record.risk_score,
                    "priority": record.priority,
                    "model_version": record.model_version,
                    "created_at": record.created_at.isoformat(),
                }
                for record in records
            ],
            "scope": SCOPE,
        }

    finally:
        db.close()



@app.post("/predict")
def predict(request: PredictionRequest) -> Dict[str, Any]:

    features = request.model_dump()

    patient_ref = features.pop("patient_ref", "anonymous")

    result = prediction_service.predict(features)

    return {
        "patient_ref": patient_ref,
        **result,
        "assessment": {
            "moca": features.get("moca"),
        },
        "scope": SCOPE,
    }


@app.post("/rank")
def rank(request: RankingRequest) -> Dict[str, Any]:

    patients = [
        patient.model_dump()
        for patient in request.patients
    ]

    results = rank_patients(
        patients=patients,
        capacity=request.capacity,
    )

    return results


@app.post("/quality")
def quality(request: QualityRequest) -> Dict[str, Any]:

    features = request.model_dump()

    features.pop("patient_ref", None)

    return calculate_quality(features)

@app.post("/assessment")
def assessment(request: PatientAssessment) -> Dict[str, Any]:

    features = request.model_dump()
    
    assessment_id = features.pop(
        "assessment_id",
        None,
    )

    patient_ref = features.pop(
        "patient_ref",
        "anonymous",
    )

    quality = calculate_quality(features)

    prediction = prediction_service.predict(features)
    explanation = explanation_service.explain(features)
    db = SessionLocal()

    try:
        record = PatientRecord(
            assessment_id=assessment_id or f"assessment-{patient_ref}",
            patient_ref=patient_ref,
            education=features.get("education"),
            mmse=features.get("mmse"),
            adas=features.get("adas"),
            faq=features.get("faq"),
            sex=features.get("sex"),
            moca=features.get("moca"),
            risk_score=prediction["risk_score"],
            priority=prediction["priority"],
            model_version=prediction["model_version"],
        )

        db.add(record)
        db.commit()
    finally:
        db.close()


    return {
        "assessment_id": assessment_id,
        "patient_ref": patient_ref,

        "assessment": {
            "education": features.get("education"),
            "sex": features.get("sex"),
            "mmse": features.get("mmse"),
            "adas": features.get("adas"),
            "moca": features.get("moca"),
            "faq": features.get("faq"),
        },

        "data_quality": quality,
        "explanation": explanation,
        "prediction": prediction,

        "workflow": {
            "current_stage": "stage1",
            "next_step": (
                "Research prioritization for further diagnostic evaluation "
                "subject to clinician review and local protocol."
            ),
        },

        "scope": SCOPE,
    }


@app.post("/explain")
def explain(request: ExplanationRequest) -> Dict[str, Any]:

    features = request.model_dump()

    features.pop("patient_ref", None)

    return explanation_service.explain(features)

@app.post("/uncertainty")
def uncertainty(request: PredictionRequest) -> Dict[str, Any]:
    features = request.model_dump()
    features.pop("patient_ref", None)

    return uncertainty_service.estimate(
        features
    )