from __future__ import annotations
from typing import List, Optional


class Task:
    def __init__(self, description: str, hour: int, frequency: int):
        """Create a task with a description, scheduled hour (0-23), and daily frequency."""
        if not 0 <= hour <= 23:
            raise ValueError(f"hour must be 0-23, got {hour}")
        if frequency < 1:
            raise ValueError(f"frequency must be at least 1, got {frequency}")
        self.description: str = description
        self.hour: int = hour          # 0-23, e.g. 8 = 8am
        self.frequency: int = frequency  # times per day
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
        return f"Task('{self.description}', hour={self.hour}, freq={self.frequency}x/day, pet={pet_name}, {status})"

    def __eq__(self, other: object) -> bool:
        """Two tasks are equal if they share the same description, hour, and frequency."""
        if not isinstance(other, Task):
            return NotImplemented
        return (
            self.description == other.description
            and self.hour == other.hour
            and self.frequency == other.frequency
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

    def mark_complete(self, task: Task) -> None:
        """Mark a task complete, validating it belongs to one of this owner's pets."""
        if task not in self.owner.get_all_tasks():
            raise ValueError(f"Task '{task.description}' does not belong to any pet under '{self.owner.name}'")
        task.mark_complete()

    def get_pending_tasks(self) -> List[Task]:
        """Return all incomplete tasks across all of this owner's pets."""
        return [task for task in self.owner.get_all_tasks() if not task.completed]

    def __repr__(self) -> str:
        """Return a readable string showing the owner and total task count."""
        return f"Scheduler(owner='{self.owner.name}', total_tasks={len(self.owner.get_all_tasks())})"
