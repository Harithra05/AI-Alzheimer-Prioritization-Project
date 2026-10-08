from typing import List, Optional

from pydantic import BaseModel, Field


class PatientAssessment(BaseModel):
    assessment_id: Optional[str] = Field(
    default=None,
    min_length=1,
    max_length=100,
)
    """
    Structured patient assessment.

    Stage-1 model inputs:
        education, mmse, adas, faq, sex

    Contextual assessment:
        moca

    MoCA is collected for assessment/context but is not used
    by the current Stage-1 model.
    """

    patient_ref: str = Field(
        default="anonymous",
        min_length=1,
        max_length=100,
    )

    # Demographic / background information
    education: Optional[float] = Field(
        default=None,
        ge=0,
        le=20,
        description="Years of education.",
    )

    sex: Optional[float] = Field(
        default=None,
        description="ADNI coding: 1=Male, 2=Female.",
    )

    # Cognitive assessment
    mmse: Optional[float] = Field(
        default=None,
        ge=0,
        le=30,
        description="MMSE total score.",
    )

    adas: Optional[float] = Field(
        default=None,
        ge=0,
        le=70,
        description="ADAS-11 total score.",
    )

    moca: Optional[float] = Field(
        default=None,
        ge=0,
        le=30,
        description="MoCA total score. Contextual only in Stage 1.",
    )

    # Functional assessment
    faq: Optional[float] = Field(
        default=None,
        ge=0,
        le=30,
        description="Functional Activities Questionnaire total.",
    )


class PredictionRequest(PatientAssessment):
    pass


class PredictionResponse(BaseModel):
    patient_ref: str
    stage: str
    risk_score: float
    priority: str
    data_quality: dict
    model_version: str
    scope: str


class RankingPatient(PatientAssessment):
    pass


class RankingRequest(BaseModel):
    patients: List[RankingPatient] = Field(
        min_length=1,
        description="Patients to rank."
    )

    capacity: Optional[int] = Field(
        default=None,
        ge=1,
        description=(
            "Optional simulated resource capacity, "
            "such as available MRI slots."
        ),
    )


class QualityRequest(PatientAssessment):
    pass


class ExplanationRequest(PatientAssessment):
    pass