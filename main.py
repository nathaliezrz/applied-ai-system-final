from pawpal_system import Task, Pet, Owner, Scheduler


def main():
    # --- Owner ---
    owner = Owner("Nathalie")

    # --- Pets ---
    buddy = Pet("Buddy", "Golden Retriever")
    luna  = Pet("Luna", "Siamese Cat")

    owner.add_pet(buddy)
    owner.add_pet(luna)

    # --- Tasks for Buddy ---
    buddy.add_task(Task("Morning walk",  hour=7,  frequency=1))
    buddy.add_task(Task("Feeding",       hour=8,  frequency=2))
    buddy.add_task(Task("Evening walk",  hour=18, frequency=1))

    # --- Tasks for Luna ---
    luna.add_task(Task("Feeding",        hour=9,  frequency=2))
    luna.add_task(Task("Grooming",       hour=14, frequency=1))

    # --- Scheduler ---
    scheduler = Scheduler(owner)

    # --- Print Today's Schedule ---
    print("=" * 40)
    print("        PAWPAL+ — TODAY'S SCHEDULE")
    print("=" * 40)
    print(f"Owner: {owner.name}\n")

    for task in scheduler.organize_tasks():
        hour_label = f"{task.hour}:00"
        status     = "[x]" if task.completed else "[ ]"
        print(f"  {status} {hour_label:<8} {task.description:<20} ({task.pet.name})")

    print()
    pending = scheduler.get_pending_tasks()
    print(f"{len(pending)} task(s) remaining today.")
    print("=" * 40)


if __name__ == "__main__":
    main()
