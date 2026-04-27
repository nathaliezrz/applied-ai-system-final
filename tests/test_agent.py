import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task
from agent import run_schedule_optimizer


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _fc(name, args=None):
    """Build a mock FunctionCall."""
    fc = MagicMock()
    fc.name = name
    fc.args = args or {}
    return fc


def _response(*calls):
    """Build a mock GenerateContentResponse with the given (name, args) tool calls."""
    r = MagicMock()
    r.candidates = [MagicMock()]
    r.candidates[0].content = MagicMock()
    r.function_calls = [_fc(name, args) for name, args in calls] if calls else []
    return r


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def conflict_owner():
    """Owner with one pet that has two tasks conflicting at 09:00."""
    today = date.today()
    owner = Owner("Test")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Feeding",    hour=9, frequency=1, due_date=today))
    pet.add_task(Task("Medication", hour=9, frequency=1, due_date=today))
    return owner


@pytest.fixture
def clean_owner():
    """Owner with one pet and no scheduling conflicts."""
    owner = Owner("Test")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Feeding", hour=8, frequency=1))
    pet.add_task(Task("Walk",    hour=9, frequency=1))
    return owner


# ── Tests ─────────────────────────────────────────────────────────────────────

@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_agent_proposes_reschedule_for_conflict(mock_client_cls, conflict_owner):
    """Agent produces a propose_reschedule entry when a conflict exists."""
    mock_client_cls.return_value.models.generate_content.side_effect = [
        _response(("get_tasks",     {})),
        _response(("get_conflicts", {})),
        _response(("propose_reschedule", {
            "pet_name":         "Buddy",
            "task_description": "Medication",
            "new_hour":         10,
            "reason":           "Avoid conflict with Feeding at 09:00",
        })),
        _response(("get_conflicts", {})),
        _response(("finish", {"summary": "Moved Medication to 10:00."})),
    ]

    result = run_schedule_optimizer(conflict_owner)

    assert len(result["proposed_changes"]) == 1
    change = result["proposed_changes"][0]
    assert change["task_description"] == "Medication"
    assert change["old_hour"] == 9
    assert change["new_hour"] == 10


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_applying_changes_clears_conflicts(mock_client_cls, conflict_owner):
    """After applying the agent's proposed changes, zero conflicts remain."""
    assert len(Scheduler(conflict_owner).get_conflicts()) == 1

    mock_client_cls.return_value.models.generate_content.side_effect = [
        _response(("get_tasks",     {})),
        _response(("get_conflicts", {})),
        _response(("propose_reschedule", {
            "pet_name":         "Buddy",
            "task_description": "Medication",
            "new_hour":         10,
            "reason":           "Avoid conflict",
        })),
        _response(("get_conflicts", {})),
        _response(("finish", {"summary": "Done."})),
    ]

    result = run_schedule_optimizer(conflict_owner)

    # Simulate what app.py does when the user clicks "Apply changes"
    for change in result["proposed_changes"]:
        for task in conflict_owner.get_all_tasks():
            if (
                task.pet
                and task.pet.name == change["pet_name"]
                and task.description == change["task_description"]
            ):
                task.hour = change["new_hour"]

    assert Scheduler(conflict_owner).get_conflicts() == []


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_agent_no_changes_on_clean_schedule(mock_client_cls, clean_owner):
    """Agent proposes nothing and finishes immediately when there are no conflicts."""
    mock_client_cls.return_value.models.generate_content.return_value = _response(
        ("finish", {"summary": "No conflicts found."})
    )

    result = run_schedule_optimizer(clean_owner)

    assert result["proposed_changes"] == []
    assert "No conflicts found." in result["summary"]


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_agent_logs_each_proposed_change(mock_client_cls, conflict_owner):
    """Every accepted propose_reschedule call produces a matching log line."""
    mock_client_cls.return_value.models.generate_content.side_effect = [
        _response(("propose_reschedule", {
            "pet_name":         "Buddy",
            "task_description": "Medication",
            "new_hour":         10,
            "reason":           "test",
        })),
        _response(("finish", {"summary": "Done."})),
    ]

    result = run_schedule_optimizer(conflict_owner)

    assert any("Medication" in line for line in result["log"])


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_agent_rejects_out_of_range_hour(mock_client_cls, conflict_owner):
    """propose_reschedule with hour > 23 is silently rejected and not recorded."""
    mock_client_cls.return_value.models.generate_content.side_effect = [
        _response(("propose_reschedule", {
            "pet_name":         "Buddy",
            "task_description": "Medication",
            "new_hour":         25,
            "reason":           "bad hour",
        })),
        _response(("finish", {"summary": "Done."})),
    ]

    result = run_schedule_optimizer(conflict_owner)

    assert result["proposed_changes"] == []


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_agent_rejects_unknown_task(mock_client_cls, conflict_owner):
    """propose_reschedule for a non-existent task is rejected and not recorded."""
    mock_client_cls.return_value.models.generate_content.side_effect = [
        _response(("propose_reschedule", {
            "pet_name":         "Buddy",
            "task_description": "Grooming",   # doesn't exist
            "new_hour":         10,
            "reason":           "test",
        })),
        _response(("finish", {"summary": "Done."})),
    ]

    result = run_schedule_optimizer(conflict_owner)

    assert result["proposed_changes"] == []


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("agent.genai.Client")
def test_agent_stops_at_max_iterations(mock_client_cls, conflict_owner):
    """Agent exits cleanly and logs a warning when MAX_ITERATIONS is reached."""
    # Always return get_conflicts — never finish — to exhaust the iteration cap.
    mock_client_cls.return_value.models.generate_content.return_value = _response(
        ("get_conflicts", {})
    )

    result = run_schedule_optimizer(conflict_owner)

    assert any("max iterations" in line.lower() for line in result["log"])
