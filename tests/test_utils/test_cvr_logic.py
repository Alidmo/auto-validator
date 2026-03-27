import pytest

from auto_validator.models.metrics import DropOffLocation, ProjectMetrics
from auto_validator.utils.cvr_logic import evaluate_cvr


@pytest.mark.parametrize("clicks,leads,drop_off,expected_tag,expected_actions", [
    # Validated: CVR > 20%
    (100, 25, "none", "Validated", ["draft_scaling_ads"]),
    (100, 21, "none", "Validated", ["draft_scaling_ads"]),
    # Refinement: CVR < 5%, landing page drop-off
    (100, 4, "landing_page", "Refinement", ["rewrite_headline"]),
    (100, 0, "landing_page", "Refinement", ["rewrite_headline"]),
    # Refinement: CVR < 5%, quiz drop-off
    (100, 3, "quiz", "Refinement", ["simplify_quiz"]),
    # Refinement: CVR < 5%, unknown drop-off → default to headline
    (100, 2, "none", "Refinement", ["rewrite_headline"]),
    # Monitoring: between thresholds
    (100, 10, "none", "Monitoring", []),
    (100, 19, "none", "Monitoring", []),
    # Edge: no clicks
    (0, 0, "none", "Monitoring", []),
])
def test_evaluate_cvr(clicks, leads, drop_off, expected_tag, expected_actions):
    metrics = ProjectMetrics(
        clicks=clicks,
        leads=leads,
        drop_off_location=DropOffLocation(drop_off),
    )
    tag, actions = evaluate_cvr(metrics)
    assert tag == expected_tag
    assert actions == expected_actions
