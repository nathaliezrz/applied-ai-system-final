from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


def print_schedule(scheduler: Scheduler) -> None:
    for task in scheduler.sort_by_time():
        status = "[x]" if task.completed else "[ ]"
        recur = f"  [{task.recurrence}]" if task.recurrence else ""
        print(f"  {status} {task.due_date}  {task.hour}:00  {task.description:<22} ({task.pet.name}){recur}")


def main():
    today = date.today()
    owner = Owner("Nathalie")

    buddy = Pet("Buddy", "Golden Retriever")
    luna  = Pet("Luna", "Siamese Cat")
    owner.add_pet(buddy)
    owner.add_pet(luna)

    # ── Normal tasks ─────────────────────────────────────────────
    buddy.add_task(Task("Morning walk",   hour=7,  frequency=1, due_date=today))
    buddy.add_task(Task("Evening walk",   hour=18, frequency=1, recurrence="daily", due_date=today))
    luna.add_task(Task("Grooming",        hour=14, frequency=1, recurrence="weekly", due_date=today))

    # ── Conflict 1: same pet, same time (both Buddy at 9:00) ─────
    buddy.add_task(Task("Feeding",        hour=9,  frequency=1, due_date=today))
    buddy.add_task(Task("Medication",     hour=9,  frequency=1, due_date=today))

    # ── Conflict 2: different pets, same time (both at 14:00) ────
    buddy.add_task(Task("Vet check-in",   hour=14, frequency=1, due_date=today))
    # Luna already has Grooming at 14:00 — this creates a cross-pet conflict

    print("=" * 56)
    print("  TODAY'S SCHEDULE")
    print("=" * 56)
    print_schedule(scheduler := Scheduler(owner))

    print("\n" + "=" * 56)
    print("  CONFLICT DETECTION")
    print("=" * 56)
    warnings = scheduler.detect_conflicts()
    if warnings:
        for w in warnings:
            print(f"  {w}")
    else:
        print("  No conflicts found.")

    print("=" * 56)


if __name__ == "__main__":
    main()
