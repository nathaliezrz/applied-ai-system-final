from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional


class Task:
    VALID_RECURRENCES = {None, "daily", "weekly"}

    def __init__(
        self,
        description: str,
        hour: int,
        frequency: int,
        recurrence: Optional[str] = None,
        due_date: Optional[date] = None,
    ):
        """Create a task with a description, scheduled hour (0-23), daily frequency,
        optional recurrence ('daily' or 'weekly'), and optional due date (defaults to today)."""
        if not 0 <= hour <= 23:
            raise ValueError(f"hour must be 0-23, got {hour}")
        if frequency < 1:
            raise ValueError(f"frequency must be at least 1, got {frequency}")
        if recurrence not in Task.VALID_RECURRENCES:
            raise ValueError(f"recurrence must be None, 'daily', or 'weekly', got '{recurrence}'")
        self.description: str = description
        self.hour: int = hour
        self.frequency: int = frequency
        self.recurrence: Optional[str] = recurrence
        self.due_date: date = due_date if due_date is not None else date.today()
        self.completed: bool = False
        self.pet: Optional[Pet] = None  # set by Pet.add_task()

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def reset(self) -> None:
        """Reset this task to incomplete, e.g. at the start of a new day."""
        self.completed = False

    def __repr__(self) -> str:
        """Return a readable string showing task details and current status."""
        pet_name = self.pet.name if self.pet else "unassigned"
        status = "done" if self.completed else "pending"
        recur = f", recurrence={self.recurrence}" if self.recurrence else ""
        return (
            f"Task('{self.description}', {self.due_date} {self.hour}:00, "
            f"freq={self.frequency}x/day, pet={pet_name}, {status}{recur})"
        )

    def __eq__(self, other: object) -> bool:
        """Two tasks are equal if they share the same description, hour, frequency, and due date."""
        if not isinstance(other, Task):
            return NotImplemented
        return (
            self.description == other.description
            and self.hour == other.hour
            and self.frequency == other.frequency
            and self.due_date == other.due_date
        )


class Pet:
    def __init__(self, name: str, breed: str):
        """Create a pet with a name and breed and an empty task list."""
        self.name: str = name
        self.breed: str = breed
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to this pet, setting the task's back-reference to this pet."""
        if task in self.tasks:
            raise ValueError(f"Task '{task.description}' is already assigned to {self.name}")
        task.pet = self
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet and clear its back-reference."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task.description}' not found for {self.name}")
        task.pet = None
        self.tasks.remove(task)

    def __repr__(self) -> str:
        """Return a readable string showing the pet's name, breed, and task count."""
        return f"Pet('{self.name}', breed='{self.breed}', tasks={len(self.tasks)})"


class Owner:
    def __init__(self, name: str):
        """Create an owner with a name and an empty pet list."""
        self.name: str = name
        self.pets: List[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        if pet in self.pets:
            raise ValueError(f"Pet '{pet.name}' is already registered to {self.name}")
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's list."""
        if pet not in self.pets:
            raise ValueError(f"Pet '{pet.name}' not found for owner {self.name}")
        self.pets.remove(pet)

    def get_all_tasks(self) -> List[Task]:
        """Return a flat list of every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def __repr__(self) -> str:
        """Return a readable string showing the owner's name and their pets."""
        return f"Owner('{self.name}', pets={[p.name for p in self.pets]})"


class Scheduler:
    def __init__(self, owner: Owner):
        """Create a scheduler tied to a specific owner."""
        self.owner: Owner = owner

    def get_tasks(self, pet: Pet) -> List[Task]:
        """Return all tasks for a pet, validating the pet belongs to this owner."""
        if pet not in self.owner.pets:
            raise ValueError(f"Pet '{pet.name}' does not belong to owner '{self.owner.name}'")
        return pet.tasks

    def organize_tasks(self) -> List[Task]:
        """Return all tasks across all pets sorted by scheduled hour."""
        return sorted(self.owner.get_all_tasks(), key=lambda t: t.hour)

    def sort_by_time(self, reverse: bool = False) -> List[Task]:
        """Return all tasks sorted by hour. Pass reverse=True for latest-first order."""
        return sorted(self.owner.get_all_tasks(), key=lambda t: t.hour, reverse=reverse)

    def mark_complete(self, task: Task) -> Optional[Task]:
        """Mark a task complete, validating it belongs to one of this owner's pets.

        If the task has a recurrence ('daily' or 'weekly'), a new Task is automatically
        created for the next occurrence and added to the same pet.

        Returns the newly scheduled Task, or None if the task has no recurrence.
        """
        if task not in self.owner.get_all_tasks():
            raise ValueError(f"Task '{task.description}' does not belong to any pet under '{self.owner.name}'")
        task.mark_complete()

        if task.recurrence is None:
            return None

        delta = timedelta(days=1 if task.recurrence == "daily" else 7)
        next_task = Task(
            task.description,
            task.hour,
            task.frequency,
            recurrence=task.recurrence,
            due_date=task.due_date + delta,
        )
        task.pet.add_task(next_task)
        return next_task

    def get_pending_tasks(self) -> List[Task]:
        """Return all incomplete tasks across all of this owner's pets."""
        return [task for task in self.owner.get_all_tasks() if not task.completed]

    def filter_tasks(self, pet_name: Optional[str] = None, completed: Optional[bool] = None) -> List[Task]:
        """Return tasks filtered by pet name and/or completion status."""
        tasks = self.owner.get_all_tasks()

        if pet_name is not None:
            matched = [p for p in self.owner.pets if p.name == pet_name]
            if not matched:
                raise ValueError(f"No pet named '{pet_name}' found for owner '{self.owner.name}'")
            tasks = [t for t in tasks if t.pet is matched[0]]

        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]

        return tasks

    def detect_conflicts(self) -> List[str]:
        """Check for tasks scheduled at the same date and hour.

        Groups all tasks by (due_date, hour). Any slot with two or more tasks
        is a conflict. Returns a list of human-readable warning strings — one per
        conflicting time slot. An empty list means no conflicts were found.
        No exceptions are raised; callers decide how to handle the warnings.
        """
        slot_map: Dict[tuple, List[Task]] = defaultdict(list)
        for task in self.owner.get_all_tasks():
            slot_map[(task.due_date, task.hour)].append(task)

        warnings: List[str] = []
        for (day, hour), tasks in sorted(slot_map.items()):
            if len(tasks) < 2:
                continue
            pet_names = [t.pet.name for t in tasks]
            same_pet = len(set(pet_names)) == 1
            if same_pet:
                task_labels = ", ".join(f"'{t.description}'" for t in tasks)
                warnings.append(
                    f"WARNING [{day} {hour}:00] {pet_names[0]} has {len(tasks)} tasks"
                    f" at the same time: {task_labels}"
                )
            else:
                task_labels = ", ".join(
                    f"'{t.description}' ({t.pet.name})" for t in tasks
                )
                warnings.append(
                    f"WARNING [{day} {hour}:00] {len(tasks)} tasks overlap across"
                    f" different pets: {task_labels}"
                )
        return warnings

    def get_conflicts(self) -> List[dict]:
        """Return structured conflict data for UI rendering.

        Each dict has:
            date     (datetime.date) — the day of the conflict
            hour     (int)           — the clashing hour (0-23)
            tasks    (List[Task])    — the tasks that overlap
            same_pet (bool)          — True if all tasks belong to the same pet
        """
        slot_map: Dict[tuple, List[Task]] = defaultdict(list)
        for task in self.owner.get_all_tasks():
            slot_map[(task.due_date, task.hour)].append(task)

        return [
            {
                "date": day,
                "hour": hour,
                "tasks": tasks,
                "same_pet": len({t.pet.name for t in tasks}) == 1,
            }
            for (day, hour), tasks in sorted(slot_map.items())
            if len(tasks) >= 2
        ]

    def __repr__(self) -> str:
        """Return a readable string showing the owner and total task count."""
        return f"Scheduler(owner='{self.owner.name}', total_tasks={len(self.owner.get_all_tasks())})"
