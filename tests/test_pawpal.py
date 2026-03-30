import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_scheduler(*task_defs):
    """Build an Owner/Pet/Scheduler from a list of (description, hour) tuples."""
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    for description, hour in task_defs:
        pet.add_task(Task(description, hour=hour, frequency=1))
    return Scheduler(owner), pet


# ── Existing tests ────────────────────────────────────────────────────────────

def test_task_completion():
    task = Task("Morning walk", hour=8, frequency=1)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_task_addition_increases_count():
    pet = Pet("Buddy", "Golden Retriever")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Morning walk", hour=8, frequency=1))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Feeding", hour=12, frequency=2))
    assert len(pet.tasks) == 2


# ── Sorting correctness ───────────────────────────────────────────────────────

def test_sort_by_time_ascending():
    """Tasks added out of order are returned earliest-first."""
    scheduler, _ = make_scheduler(
        ("Evening walk", 18),
        ("Feeding",      12),
        ("Morning walk",  7),
    )
    hours = [t.hour for t in scheduler.sort_by_time()]
    assert hours == sorted(hours)


def test_sort_by_time_descending():
    """reverse=True returns tasks latest-first."""
    scheduler, _ = make_scheduler(
        ("Morning walk",  7),
        ("Feeding",      12),
        ("Evening walk", 18),
    )
    hours = [t.hour for t in scheduler.sort_by_time(reverse=True)]
    assert hours == sorted(hours, reverse=True)


def test_sort_boundary_hours():
    """Tasks at midnight (0) and 11 PM (23) sort to the correct extremes."""
    scheduler, _ = make_scheduler(
        ("Late meds",  23),
        ("Midnight",    0),
        ("Midday",     12),
    )
    hours = [t.hour for t in scheduler.sort_by_time()]
    assert hours[0] == 0
    assert hours[-1] == 23


def test_sort_single_task():
    """A single task is returned unchanged."""
    scheduler, _ = make_scheduler(("Feeding", 9))
    result = scheduler.sort_by_time()
    assert len(result) == 1
    assert result[0].hour == 9


def test_sort_empty_pet():
    """No tasks returns an empty list without error."""
    owner = Owner("Test Owner")
    owner.add_pet(Pet("Buddy", "Golden Retriever"))
    scheduler = Scheduler(owner)
    assert scheduler.sort_by_time() == []


# ── Recurrence logic ──────────────────────────────────────────────────────────

def test_daily_recurrence_creates_next_day_task():
    """Completing a daily task adds a new task dated tomorrow."""
    today = date.today()
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Morning walk", hour=7, frequency=1,
                      recurrence="daily", due_date=today))

    scheduler = Scheduler(owner)
    next_task = scheduler.mark_complete(pet.tasks[0])

    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.hour == 7
    assert next_task.description == "Morning walk"
    assert next_task.recurrence == "daily"
    assert next_task.completed is False


def test_weekly_recurrence_creates_task_seven_days_later():
    """Completing a weekly task adds a new task dated 7 days ahead."""
    today = date.today()
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Flea treatment", hour=9, frequency=1,
                      recurrence="weekly", due_date=today))

    scheduler = Scheduler(owner)
    next_task = scheduler.mark_complete(pet.tasks[0])

    assert next_task.due_date == today + timedelta(days=7)


def test_no_recurrence_returns_none():
    """Completing a one-off task returns None and adds no new task."""
    scheduler, pet = make_scheduler(("Vet visit", 10))
    initial_count = len(pet.tasks)

    result = scheduler.mark_complete(pet.tasks[0])

    assert result is None
    assert len(pet.tasks) == initial_count


def test_recurring_task_is_added_to_same_pet():
    """The auto-created next occurrence belongs to the same pet."""
    today = date.today()
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Feeding", hour=8, frequency=1,
                      recurrence="daily", due_date=today))

    scheduler = Scheduler(owner)
    next_task = scheduler.mark_complete(pet.tasks[0])

    assert next_task in pet.tasks
    assert next_task.pet is pet


# ── Conflict detection ────────────────────────────────────────────────────────

def test_same_pet_conflict_detected():
    """Two tasks for the same pet at the same hour are flagged."""
    today = date.today()
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Feeding",    hour=9, frequency=1, due_date=today))
    pet.add_task(Task("Medication", hour=9, frequency=1, due_date=today))

    conflicts = Scheduler(owner).get_conflicts()

    assert len(conflicts) == 1
    assert conflicts[0]["same_pet"] is True
    assert conflicts[0]["hour"] == 9


def test_cross_pet_conflict_detected():
    """Two tasks for different pets at the same hour are flagged."""
    today = date.today()
    owner = Owner("Test Owner")
    buddy = Pet("Buddy", "Golden Retriever")
    luna  = Pet("Luna",  "Siamese Cat")
    owner.add_pet(buddy)
    owner.add_pet(luna)
    buddy.add_task(Task("Vet check-in", hour=14, frequency=1, due_date=today))
    luna.add_task(Task("Grooming",      hour=14, frequency=1, due_date=today))

    conflicts = Scheduler(owner).get_conflicts()

    assert len(conflicts) == 1
    assert conflicts[0]["same_pet"] is False
    assert conflicts[0]["hour"] == 14


def test_no_conflict_when_different_hours():
    """Tasks at different hours do not produce a conflict."""
    scheduler, _ = make_scheduler(("Feeding", 8), ("Walk", 9))
    assert scheduler.get_conflicts() == []


def test_no_conflict_on_empty_schedule():
    """No tasks means no conflicts."""
    owner = Owner("Test Owner")
    owner.add_pet(Pet("Buddy", "Golden Retriever"))
    assert Scheduler(owner).get_conflicts() == []


def test_same_hour_different_dates_no_conflict():
    """Tasks at the same hour but on different dates are not a conflict."""
    today = date.today()
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    pet.add_task(Task("Feeding", hour=9, frequency=1, due_date=today))
    pet.add_task(Task("Feeding", hour=9, frequency=1, due_date=today + timedelta(days=1)))

    assert Scheduler(owner).get_conflicts() == []


def test_conflict_reports_all_clashing_tasks():
    """Three tasks at the same slot are all included in one conflict entry."""
    today = date.today()
    owner = Owner("Test Owner")
    pet = Pet("Buddy", "Golden Retriever")
    owner.add_pet(pet)
    for title in ("Walk", "Feeding", "Medication"):
        pet.add_task(Task(title, hour=9, frequency=1, due_date=today))

    conflicts = Scheduler(owner).get_conflicts()

    assert len(conflicts) == 1
    assert len(conflicts[0]["tasks"]) == 3
