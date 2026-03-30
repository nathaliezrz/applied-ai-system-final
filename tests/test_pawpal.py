import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Task, Pet


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
