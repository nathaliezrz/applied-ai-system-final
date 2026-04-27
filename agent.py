import logging
import os
from collections import defaultdict

from google import genai
from google.genai import types

from pawpal_system import Owner

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10

SYSTEM_PROMPT = (
    "You are the PawPal+ Schedule Optimizer. Resolve all scheduling conflicts "
    "in the pet care schedule by proposing task rescheduling.\n\n"
    "Workflow:\n"
    "1. Call get_tasks to see the full schedule.\n"
    "2. Call get_conflicts to find overlapping tasks.\n"
    "3. For each conflict, call propose_reschedule to move one task to a free hour.\n"
    "4. Call get_conflicts again — proposed changes are already reflected.\n"
    "5. Repeat until no conflicts remain, then call finish.\n\n"
    "Rules:\n"
    "- Choose the nearest free hour (prefer ±1 or ±2 from the original).\n"
    "- Never reschedule a completed task.\n"
    "- If there are no conflicts at all, call finish immediately."
)

_TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_tasks",
                description="Return all current tasks across all pets.",
            ),
            types.FunctionDeclaration(
                name="get_conflicts",
                description=(
                    "Return all scheduling conflicts — time slots where two or more tasks overlap. "
                    "Call this after each propose_reschedule to check if conflicts remain."
                ),
            ),
            types.FunctionDeclaration(
                name="propose_reschedule",
                description=(
                    "Propose moving a task to a new hour to resolve a conflict. "
                    "The change is queued for human review but immediately reflected "
                    "in subsequent get_conflicts calls."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name":         types.Schema(type=types.Type.STRING),
                        "task_description": types.Schema(type=types.Type.STRING),
                        "new_hour":         types.Schema(type=types.Type.INTEGER, description="0-23"),
                        "reason":           types.Schema(type=types.Type.STRING),
                    },
                    required=["pet_name", "task_description", "new_hour", "reason"],
                ),
            ),
            types.FunctionDeclaration(
                name="finish",
                description="Signal that optimization is complete and provide a summary.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "summary": types.Schema(type=types.Type.STRING),
                    },
                    required=["summary"],
                ),
            ),
        ]
    )
]


def run_schedule_optimizer(owner: Owner) -> dict:
    """Run the Gemini AI agent to produce proposed schedule changes.

    Returns:
        proposed_changes  list[{pet_name, task_description, old_hour, new_hour, reason}]
        summary           str
        log               list[str]
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    proposed_changes: list[dict] = []
    log: list[str] = []
    summary = "No changes proposed."

    # working_hours reflects proposals already made so get_conflicts stays accurate.
    working_hours: dict[tuple, int] = {
        (t.pet.name, t.description): t.hour
        for t in owner.get_all_tasks()
        if t.pet
    }

    def _get_tasks() -> dict:
        rows = []
        for t in owner.get_all_tasks():
            if not t.pet:
                continue
            key = (t.pet.name, t.description)
            rows.append({
                "pet":         t.pet.name,
                "description": t.description,
                "hour":        working_hours.get(key, t.hour),
                "frequency":   t.frequency,
                "recurrence":  t.recurrence or "none",
                "completed":   t.completed,
            })
        return {"tasks": rows}

    def _get_conflicts() -> dict:
        slot_map: dict[tuple, list] = defaultdict(list)
        for t in owner.get_all_tasks():
            if not t.pet:
                continue
            key = (t.pet.name, t.description)
            hour = working_hours.get(key, t.hour)
            slot_map[(str(t.due_date), hour)].append(
                {"pet": t.pet.name, "description": t.description}
            )
        conflicts = [
            {"date": date_str, "hour": hour, "tasks": tasks}
            for (date_str, hour), tasks in sorted(slot_map.items())
            if len(tasks) >= 2
        ]
        return {"conflicts": conflicts}

    def _propose_reschedule(pet_name: str, task_description: str, new_hour: int, reason: str) -> dict:
        new_hour = int(new_hour)
        if not 0 <= new_hour <= 23:
            return {"error": f"new_hour must be 0-23, got {new_hour}"}
        key = (pet_name, task_description)
        if key not in working_hours:
            return {"error": f"Task '{task_description}' for pet '{pet_name}' not found"}
        old_hour = working_hours[key]
        working_hours[key] = new_hour
        proposed_changes.append({
            "pet_name":         pet_name,
            "task_description": task_description,
            "old_hour":         old_hour,
            "new_hour":         new_hour,
            "reason":           reason,
        })
        msg = f"Proposed: '{task_description}' ({pet_name}) {old_hour:02d}:00 → {new_hour:02d}:00"
        log.append(msg)
        logger.info(msg)
        return {"ok": True}

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=_TOOLS,
    )

    # Pre-load context so the agent skips get_tasks/get_conflicts lookup calls.
    import json as _json
    _initial = (
        "Optimise the schedule by resolving all conflicts.\n\n"
        f"Current tasks:\n{_json.dumps(_get_tasks(), indent=2)}\n\n"
        f"Current conflicts:\n{_json.dumps(_get_conflicts(), indent=2)}\n\n"
        "Use propose_reschedule for each conflict, then call finish."
    )

    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=_initial)])
    ]

    logger.info("Schedule optimizer started")
    log.append("Optimizer started.")

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d", iteration + 1)

        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=contents,
            config=config,
        )

        if not response.candidates:
            log.append("Response blocked or empty — stopping.")
            logger.warning("Empty candidates at iteration %d", iteration + 1)
            break

        # Append the model turn to history.
        contents.append(response.candidates[0].content)

        function_calls = response.function_calls
        if not function_calls:
            log.append("Agent finished (no function calls).")
            break

        response_parts: list[types.Part] = []
        done = False
        for fc in function_calls:
            args = dict(fc.args) if fc.args else {}
            logger.info("Tool call: %s %s", fc.name, args)

            if fc.name == "get_tasks":
                result = _get_tasks()
            elif fc.name == "get_conflicts":
                result = _get_conflicts()
            elif fc.name == "propose_reschedule":
                result = _propose_reschedule(**args)
            elif fc.name == "finish":
                summary = args.get("summary", "Optimization complete.")
                log.append(f"Summary: {summary}")
                logger.info("Agent finished: %s", summary)
                done = True
                result = {"ok": True}
            else:
                result = {"error": f"Unknown tool: {fc.name}"}

            response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response=result,
                    )
                )
            )

        # Append the function responses as a user turn.
        contents.append(
            types.Content(role="user", parts=response_parts)
        )

        if done:
            break
    else:
        log.append(f"Reached max iterations ({MAX_ITERATIONS}).")
        logger.warning("Agent hit max iterations")

    return {"proposed_changes": proposed_changes, "summary": summary, "log": log}
