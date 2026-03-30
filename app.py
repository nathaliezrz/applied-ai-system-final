import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

# Vault check: only create the Owner and Pet once; reuse them on every rerun
if "owner" not in st.session_state:
    st.session_state.owner = Owner(owner_name)
if "pet" not in st.session_state:
    pet = Pet(pet_name, species)
    st.session_state.owner.add_pet(pet)
    st.session_state.pet = pet

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    task_hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=8)
with col3:
    task_freq = st.number_input("Times per day", min_value=1, max_value=10, value=1)

if st.button("Add task"):
    try:
        task = Task(task_title, hour=int(task_hour), frequency=int(task_freq))
        st.session_state.pet.add_task(task)
        st.session_state.tasks.append(
            {"title": task.description, "hour": task.hour, "times/day": task.frequency}
        )
    except ValueError as e:
        st.error(str(e))

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    if not st.session_state.pet.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(st.session_state.owner)
        st.markdown(f"**Owner:** {st.session_state.owner.name} | **Pet:** {st.session_state.pet.name}")
        st.markdown("---")
        for task in scheduler.organize_tasks():
            status = "✅" if task.completed else "⬜"
            st.markdown(f"{status} **{task.hour}:00** — {task.description} ({task.frequency}x/day)")
        pending = scheduler.get_pending_tasks()
        st.caption(f"{len(pending)} task(s) remaining today.")
