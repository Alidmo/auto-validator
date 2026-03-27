import pytest

from auto_validator.utils.prompt_loader import load_prompt


def test_load_strategist_angles_prompt():
    system, user = load_prompt("strategist", "generate_angles", idea="A CRM for freelance designers")
    assert len(system) > 50
    assert "A CRM for freelance designers" in user
    assert "story" in user.lower()
    assert "controversy" in user.lower()


def test_load_validates_equation_prompt():
    system, user = load_prompt(
        "strategist", "validate_equation",
        idea="Test idea",
        angle_type="story",
        angle_headline="Test headline",
        avatar_name="Alice",
        avatar_age_range="30-40",
        avatar_occupation="Designer",
        top_pain_point="Too many revisions",
        desired_outcome="Clients who respect my time",
    )
    assert "Timeless Equation" in system
    assert "Alice" in user


def test_missing_prompt_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("strategist", "nonexistent_prompt", idea="x")


def test_missing_variable_raises():
    from jinja2 import UndefinedError
    with pytest.raises(UndefinedError):
        load_prompt("strategist", "generate_angles")  # missing 'idea'
