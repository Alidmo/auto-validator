"""Tests for JsonFileStore state persistence."""
from pathlib import Path

import pytest

from auto_validator.exceptions import ProjectNotFoundError
from auto_validator.models.project import ProjectState, ProjectStatus
from auto_validator.state.json_store import JsonFileStore


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_store(tmp_path: Path) -> JsonFileStore:
    """Return a JsonFileStore pointing at a temp directory."""
    return JsonFileStore(data_dir=tmp_path / "projects")


def _make_state(idea: str = "A test business idea") -> ProjectState:
    return ProjectState(idea=idea)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_save_and_load(tmp_path):
    """Save a project, load it back, verify identical."""
    store = _make_store(tmp_path)
    state = _make_state("A productivity app for kindergarten teachers")

    store.save(state)
    loaded = store.load(state.project_id)

    assert loaded.project_id == state.project_id
    assert loaded.idea == state.idea
    assert loaded.status == state.status


def test_save_creates_json_file(tmp_path):
    """Saving a project creates a JSON file on disk."""
    store = _make_store(tmp_path)
    state = _make_state("File creation test")

    store.save(state)

    expected_path = tmp_path / "projects" / f"{state.project_id}.json"
    assert expected_path.exists()
    assert expected_path.stat().st_size > 0


def test_list_all(tmp_path):
    """Save multiple projects, list returns all of them."""
    store = _make_store(tmp_path)

    ideas = [
        "A meditation app for nurses",
        "A meal-kit service for college students",
        "A budgeting tool for freelancers",
    ]
    saved_ids = set()
    for idea in ideas:
        state = _make_state(idea)
        store.save(state)
        saved_ids.add(state.project_id)

    all_projects = store.list_all()

    assert len(all_projects) == 3
    loaded_ids = {p.project_id for p in all_projects}
    assert loaded_ids == saved_ids


def test_list_all_empty_directory(tmp_path):
    """list_all returns empty list when no projects are saved."""
    store = _make_store(tmp_path)
    result = store.list_all()
    assert result == []


def test_delete(tmp_path):
    """Save then delete a project; subsequent load raises ProjectNotFoundError."""
    store = _make_store(tmp_path)
    state = _make_state("Delete-me project")

    store.save(state)
    # Confirm it exists
    loaded = store.load(state.project_id)
    assert loaded.project_id == state.project_id

    # Delete it
    store.delete(state.project_id)

    # Now it should be gone
    with pytest.raises(ProjectNotFoundError):
        store.load(state.project_id)


def test_delete_removes_file(tmp_path):
    """Deleting a project removes its JSON file from disk."""
    store = _make_store(tmp_path)
    state = _make_state("File removal test")

    store.save(state)
    file_path = tmp_path / "projects" / f"{state.project_id}.json"
    assert file_path.exists()

    store.delete(state.project_id)
    assert not file_path.exists()


def test_load_missing(tmp_path):
    """Loading a nonexistent project raises ProjectNotFoundError."""
    store = _make_store(tmp_path)

    with pytest.raises(ProjectNotFoundError):
        store.load("this-project-does-not-exist")


def test_delete_missing_raises(tmp_path):
    """Deleting a nonexistent project raises ProjectNotFoundError."""
    store = _make_store(tmp_path)

    with pytest.raises(ProjectNotFoundError):
        store.delete("nonexistent-project-id")


def test_save_updates_existing(tmp_path):
    """Saving a modified state overwrites the previous file."""
    store = _make_store(tmp_path)
    state = _make_state("Overwrite test idea")

    store.save(state)
    original_updated_at = store.load(state.project_id).updated_at

    # Mutate and re-save
    state.status = ProjectStatus.A_COMPLETE
    store.save(state)

    reloaded = store.load(state.project_id)
    assert reloaded.status == ProjectStatus.A_COMPLETE
    # updated_at should have advanced (touch() is called on save)
    assert reloaded.updated_at >= original_updated_at


def test_list_all_sorted_by_modification_time(tmp_path):
    """list_all returns projects sorted by most recently modified first."""
    store = _make_store(tmp_path)

    first = _make_state("First project")
    second = _make_state("Second project")
    third = _make_state("Third project")

    store.save(first)
    store.save(second)
    store.save(third)

    # Re-save first to make it the most recently modified
    store.save(first)

    all_projects = store.list_all()

    # The first project was re-saved last, so it should appear first in the list
    assert all_projects[0].project_id == first.project_id


def test_list_all_skips_corrupt_files(tmp_path):
    """list_all silently skips JSON files that cannot be parsed."""
    store = _make_store(tmp_path)
    state = _make_state("Valid project")
    store.save(state)

    # Plant a corrupt JSON file
    corrupt_path = tmp_path / "projects" / "corrupt-file.json"
    corrupt_path.write_text("{ this is not valid json !!!}", encoding="utf-8")

    all_projects = store.list_all()

    # Only the valid project should be returned
    assert len(all_projects) == 1
    assert all_projects[0].project_id == state.project_id


def test_loaded_state_has_correct_idea(tmp_path):
    """Loaded state preserves the exact idea string."""
    store = _make_store(tmp_path)
    idea = "A very specific niche idea with special chars: café & résumé"
    state = ProjectState(idea=idea)

    store.save(state)
    loaded = store.load(state.project_id)

    assert loaded.idea == idea


def test_save_initialises_data_dir_if_missing(tmp_path):
    """JsonFileStore creates the data directory if it doesn't exist yet."""
    deep_path = tmp_path / "a" / "b" / "c" / "projects"
    assert not deep_path.exists()

    store = JsonFileStore(data_dir=deep_path)
    state = _make_state("Dir creation test")
    store.save(state)

    assert deep_path.exists()
    assert (deep_path / f"{state.project_id}.json").exists()
