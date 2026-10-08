from typing import Any, Dict


STAGE1_FEATURES = [
    "education",
    "mmse",
    "adas",
    "faq",
    "sex",
]

CONTEXTUAL_FEATURES = [
    "moca",
]


def calculate_quality(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate completeness and basic quality warnings.

    This is a data-quality indicator only.
    It is not a measure of diagnostic certainty.
    """

    available = []
    missing = []

    for feature in STAGE1_FEATURES:
        value = features.get(feature)

        if value is None:
            missing.append(feature)
        else:
            available.append(feature)

    total = len(STAGE1_FEATURES)

    completeness = (
        len(available) / total
        if total > 0
        else 0.0
    )

    if completeness == 1.0:
        level = "GOOD"
    elif completeness >= 0.6:
        level = "LIMITED"
    else:
        level = "POOR"

    warnings = []

    if "mmse" in missing:
        warnings.append(
            "MMSE is missing; the model will use its preprocessing strategy."
        )

    if "adas" in missing:
        warnings.append(
            "ADAS is missing; the model will use its preprocessing strategy."
        )

    if "faq" in missing:
        warnings.append(
            "FAQ is missing; the model will use its preprocessing strategy."
        )

    if "education" in missing:
        warnings.append(
            "Education is missing; the model will use its preprocessing strategy."
        )

    if "sex" in missing:
        warnings.append(
            "Sex is missing; the model will use its preprocessing strategy."
        )

    if features.get("moca") is None:
        warnings.append(
            "MoCA is unavailable. This does not prevent Stage-1 prediction "
            "because MoCA is not a Stage-1 model input."
        )

    return {
        "available": len(available),
        "total": total,
        "completeness": round(completeness, 4),
        "level": level,
        "available_features": available,
        "missing_features": missing,
        "warnings": warnings,
        "contextual_data": {
            "moca_available": features.get("moca") is not None,
        },
        "interpretation": (
            "Data completeness indicator only; "
            "not a measure of clinical certainty."
        ),
    }