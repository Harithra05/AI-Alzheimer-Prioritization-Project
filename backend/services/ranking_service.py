from typing import Any, Dict, List, Optional

from backend.services.prediction_service import prediction_service


def rank_patients(
    patients: List[Dict[str, Any]],
    capacity: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate calibrated model risk scores and rank patients
    from highest to lowest estimated progression risk.

    An optional capacity simulates a limited diagnostic resource,
    such as a fixed number of available MRI slots.

    This is a retrospective/research prioritization function.
    It does not make a clinical diagnosis or treatment decision.
    """

    results = []

    for patient in patients:
        assessment_id = patient.get("assessment_id")

        patient_ref = patient.get(
            "patient_ref",
            "anonymous",
        )

        prediction = prediction_service.predict(patient)

        results.append(
            {
                "assessment_id": assessment_id,
                "patient_ref": patient_ref,
                "risk_score": prediction["risk_score"],
                "priority": prediction["priority"],
                "data_quality": prediction["data_quality"],
                "stage": prediction["stage"],
                "model_version": prediction["model_version"],
            }
        )

    # Highest estimated risk first.
    results.sort(
        key=lambda x: x["risk_score"],
        reverse=True,
    )

    total = len(results)

    # Assign rank and percentile.
    for index, patient in enumerate(
        results,
        start=1,
    ):

        patient["rank"] = index

        if total > 1:
            patient["percentile"] = round(
                100 * (total - index) / (total - 1),
                2,
            )
        else:
            patient["percentile"] = 100.0

    # Simulated resource capacity.
    selected_count = 0

    if capacity is not None:

        if capacity < 1:
            raise ValueError(
                "Capacity must be greater than or equal to 1."
            )

        selected_count = min(
            capacity,
            total,
        )

        for index, patient in enumerate(results):

            patient["selected_for_capacity"] = (
                index < selected_count
            )

    else:

        for patient in results:
            patient["selected_for_capacity"] = False

    # Cohort-level statistics.
    risk_scores = [
        patient["risk_score"]
        for patient in results
    ]

    high_count = sum(
        patient["priority"] == "HIGH"
        for patient in results
    )

    medium_count = sum(
        patient["priority"] == "MEDIUM"
        for patient in results
    )

    low_count = sum(
        patient["priority"] == "LOW"
        for patient in results
    )

    if risk_scores:

        mean_risk = (
            sum(risk_scores) /
            len(risk_scores)
        )

        maximum_risk = max(risk_scores)
        minimum_risk = min(risk_scores)

    else:

        mean_risk = 0.0
        maximum_risk = 0.0
        minimum_risk = 0.0

    return {
        "stage": prediction_service.stage,

        "model_version": (
            prediction_service.model_version
        ),

        "total_patients": total,

        "capacity": capacity,

        "selected_count": selected_count,

        "cohort_summary": {
            "mean_risk": round(
                mean_risk,
                6,
            ),
            "minimum_risk": round(
                minimum_risk,
                6,
            ),
            "maximum_risk": round(
                maximum_risk,
                6,
            ),
            "high_priority_count": high_count,
            "medium_priority_count": medium_count,
            "low_priority_count": low_count,
        },

        "patients": results,

        "scope": (
            "Research clinical decision-support prototype; "
            "ranking supports prioritization research only "
            "and does not determine diagnosis or treatment."
        ),
    }