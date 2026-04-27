import logging
import os

import streamlit as st

from agent import run_schedule_optimizer
from pawpal_system import Owner, Pet, Scheduler, Task

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pawpal_agent.log")
_log_handler = logging.FileHandler(_LOG_PATH)
_log_handler.setLevel(logging.INFO)
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

for _name in ("agent", __name__):
    _lg = logging.getLogger(_name)
    _lg.setLevel(logging.INFO)
    if not any(isinstance(h, logging.FileHandler) for h in _lg.handlers):
        _lg.addHandler(_log_handler)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.divider()

# ── Setup ─────────────────────────────────────────────────────────────────────
st.subheader("Setup")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if "owner" not in st.session_state:
    st.session_state.owner = Owner(owner_name)
if "pet" not in st.session_state:
    pet = Pet(pet_name, species)
    st.session_state.owner.add_pet(pet)
    st.session_state.pet = pet

if "tasks" not in st.session_state:
    st.session_state.tasks = []

st.divider()

# ── Add a Task ────────────────────────────────────────────────────────────────
st.subheader("Add a Task")

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    task_hour = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=8)
with col3:
    task_freq = st.number_input("Times per day", min_value=1, max_value=10, value=1)
with col4:
    task_recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"])

if st.button("Add task"):
    try:
        recurrence = None if task_recurrence == "none" else task_recurrence
        task = Task(task_title, hour=int(task_hour), frequency=int(task_freq), recurrence=recurrence)
        st.session_state.pet.add_task(task)
        st.session_state.tasks.append({
            "Title": task.description,
            "Hour": task.hour,
            "Times/day": task.frequency,
            "Recurrence": task_recurrence,
        })
        st.success(f"'{task.description}' added at {task.hour}:00.")
    except ValueError as e:
        st.error(str(e))

if st.session_state.tasks:
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# ── Schedule ──────────────────────────────────────────────────────────────────
st.subheader("Today's Schedule")

if not st.session_state.pet.tasks:
    st.info("Add at least one task to see your schedule.")
else:
    scheduler = Scheduler(st.session_state.owner)

    # ── Conflict cards ────────────────────────────────────────────
    conflicts = scheduler.get_conflicts()
    if conflicts:
        st.error(
            f"**{len(conflicts)} scheduling conflict(s) found.** "
            "Review and adjust task times to avoid overlap."
        )
        for c in conflicts:
            time_str = f"{c['hour']:02d}:00"
            if c["same_pet"]:
                pet_label = c["tasks"][0].pet.name
                header = f"⚠️ {pet_label} — {len(c['tasks'])} tasks at {time_str}"
            else:
                pets = " & ".join({t.pet.name for t in c["tasks"]})
                header = f"⚠️ {pets} — overlapping tasks at {time_str}"

            with st.expander(header, expanded=True):
                st.table([
                    {
                        "Task": t.description,
                        "Pet": t.pet.name,
                        "Recurrence": t.recurrence or "one-off",
                        "Status": "Done" if t.completed else "Pending",
                    }
                    for t in c["tasks"]
                ])
                st.caption("Tip: move one of these tasks to a different hour to resolve the conflict.")
    else:
        st.success("No scheduling conflicts — your day is well organised!")

    st.markdown("---")

    # ── Filters ───────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        sort_order = st.radio("Sort order", ["Earliest first", "Latest first"], horizontal=True)
    with col_b:
        status_filter = st.radio("Show", ["All", "Pending", "Completed"], horizontal=True)

    # ── Build filtered + sorted list ──────────────────────────────
    completed_map = {"All": None, "Pending": False, "Completed": True}
    filtered = scheduler.filter_tasks(completed=completed_map[status_filter])
    reverse = sort_order == "Latest first"
    sorted_tasks = sorted(filtered, key=lambda t: t.hour, reverse=reverse)

    # ── Summary metrics ───────────────────────────────────────────
    total = len(scheduler.filter_tasks())
    pending_count = len(scheduler.filter_tasks(completed=False))
    done_count = total - pending_count

    m1, m2, m3 = st.columns(3)
    m1.metric("Total tasks", total)
    m2.metric("Pending", pending_count)
    m3.metric("Completed", done_count)

    st.markdown("---")

    # ── Schedule table ────────────────────────────────────────────
    if not sorted_tasks:
        st.info("No tasks match the current filter.")
    else:
        st.table([
            {
                "Time": f"{t.hour:02d}:00",
                "Task": t.description,
                "Pet": t.pet.name,
                "Times/day": t.frequency,
                "Recurrence": t.recurrence or "—",
                "Status": "✅ Done" if t.completed else "⬜ Pending",
            }
            for t in sorted_tasks
        ])

st.divider()

# ── AI Schedule Optimizer ─────────────────────────────────────────────────────
st.subheader("AI Schedule Optimizer")

if not os.environ.get("GEMINI_API_KEY"):
    st.warning("Set the GEMINI_API_KEY environment variable to enable the AI optimizer.")
elif not st.session_state.pet.tasks:
    st.info("Add tasks above to use the AI optimizer.")
else:
    _scheduler = Scheduler(st.session_state.owner)
    _conflicts = _scheduler.get_conflicts()

    if not _conflicts:
        st.success("No conflicts detected — your schedule is already optimal.")
    else:
        st.warning(
            f"{len(_conflicts)} conflict(s) found. "
            "The AI agent will propose fixes for your review."
        )

    if _conflicts and st.button("Optimize with AI"):
        with st.spinner("Running AI agent (plan → act → check)..."):
            try:
                result = run_schedule_optimizer(st.session_state.owner)
                st.session_state.agent_result = result
                logger.info("Agent returned %d proposed change(s)", len(result["proposed_changes"]))
            except Exception as exc:
                st.error(f"Agent error: {exc}")
                logger.exception("Agent failed")

    if st.session_state.get("agent_result"):
        result = st.session_state.agent_result

        with st.expander("Agent reasoning log", expanded=False):
            for line in result["log"]:
                st.text(line)

        if result["proposed_changes"]:
            st.markdown("**Proposed changes — review before applying:**")
            st.table([
                {
                    "Pet":  c["pet_name"],
                    "Task": c["task_description"],
                    "From": f"{c['old_hour']:02d}:00",
                    "To":   f"{c['new_hour']:02d}:00",
                    "Reason": c["reason"],
                }
                for c in result["proposed_changes"]
            ])

            col_apply, col_discard = st.columns(2)
            with col_apply:
                if st.button("Apply changes", type="primary"):
                    for change in result["proposed_changes"]:
                        for task in st.session_state.owner.get_all_tasks():
                            if (
                                task.pet
                                and task.pet.name == change["pet_name"]
                                and task.description == change["task_description"]
                            ):
                                task.hour = change["new_hour"]
                                logger.info(
                                    "Applied: '%s' (%s) %02d:00 → %02d:00",
                                    task.description, task.pet.name,
                                    change["old_hour"], change["new_hour"],
                                )
                                break
                    # Rebuild display list to stay in sync
                    st.session_state.tasks = [
                        {
                            "Title":      t.description,
                            "Hour":       t.hour,
                            "Times/day":  t.frequency,
                            "Recurrence": t.recurrence or "none",
                        }
                        for t in st.session_state.owner.get_all_tasks()
                    ]
                    st.session_state.agent_result = None
                    st.success("Changes applied! Scroll up to see your updated schedule.")
                    st.rerun()
            with col_discard:
                if st.button("Discard"):
                    st.session_state.agent_result = None
                    st.rerun()
        else:
            st.info(f"Agent summary: {result['summary']}")
            if st.button("OK"):
                st.session_state.agent_result = None
                st.rerun()
