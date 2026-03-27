from auto_validator.config import settings
from auto_validator.models.metrics import DropOffLocation, ProjectMetrics


def evaluate_cvr(metrics: ProjectMetrics) -> tuple[str, list[str]]:
    """
    Apply CVR threshold logic.

    Returns:
        (status_tag, actions)  — pure function, no side effects.

    Actions vocabulary:
        "draft_scaling_ads"   — CVR > threshold, generate broader ad variations
        "rewrite_headline"    — CVR < threshold, drop-off at landing page
        "simplify_quiz"       — CVR < threshold, drop-off at quiz
    """
    if metrics.clicks == 0:
        return "Monitoring", []

    cvr = metrics.cvr

    if cvr > settings.cvr_validated_threshold:
        return "Validated", ["draft_scaling_ads"]

    if cvr < settings.cvr_refinement_threshold:
        if metrics.drop_off_location == DropOffLocation.LANDING_PAGE:
            return "Refinement", ["rewrite_headline"]
        elif metrics.drop_off_location == DropOffLocation.QUIZ:
            return "Refinement", ["simplify_quiz"]
        else:
            return "Refinement", ["rewrite_headline"]

    return "Monitoring", []
