# PawPal+

## Original Project

PawPal+ was originally built in Modules 1–3 as a pet care scheduling app. The goal was to help a busy owner track tasks (walks, feeding, medication) across multiple pets, detect scheduling conflicts, and view a sorted, filterable daily plan. The core system used four classes: 'Task', 'Pet', 'Owner', and 'Scheduler.' Each with logic for recurrence, conflict detection, and time-based sorting.

## What It Does Now

PawPal+ now includes an AI Schedule Optimizer powered by the Gemini API. When conflicts are detected, the AI agent analyzes the schedule, proposes rescheduling fixes, and presents them for human review before anything changes.

## Architecture Overview

```
User → Streamlit UI → Owner/Pet/Task Data Model → Scheduler
                                                       ↓
                                               AI Agent (Gemini)
                                          plan → act → check loop
                                                       ↓
                                            Human Review (Apply / Discard)
                                                       ↓
                                            Optimised Schedule + Log
```

The agent uses four tools: 'get_tasks', 'get_conflicts', 'propose_reschedule', and 'finish'. It receives the current schedule and conflicts upfront, proposes fixes, and iterates until no conflicts remain. All actions are logged to 'pawpal_agent.log'.

## Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd applied-ai-system-final

# 2. Install requirements
pip install -r requirements.txt

# 3. Set your Gemini API key
export GEMINI_API_KEY="your-key-here"

# 4. Run the app
streamlit run app.py

# 5. (Optional) Watch the agent log in a second terminal
tail -f pawpal_agent.log
```

#Run tests:
```bash
python3 -m pytest tests/ -v
```

## Sample Interactions

**Case 1 — Conflict resolved**

Input: Feeding at 09:00, Medication at 09:00 (conflict), Evening walk at 18:00

AI output:
```
Proposed: 'Medication' (Mochi) 09:00 → 10:00
Reason: Avoid conflict with Feeding scheduled at 09:00
```
After applying → zero conflicts, schedule updates immediately.

---

**Case 2 — Clean schedule**

Input: Feeding at 08:00, Walk at 09:00 (no conflict)

AI output: Calls `finish` immediately.
```
Summary: No conflicts found. Schedule is already optimal.
```

---

**Case 3 — Guardrail: missing API key**

Input: GEMINI_API_KEY not set

Output: Yellow warning banner — "Set the GEMINI_API_KEY environment variable to enable the AI optimizer." Button is hidden; rest of app works normally.

## Design Decisions

| Decision | Reason | Trade-off |
|---|---|---|
| Proposals shown before applying | Keeps the human in control | Extra click required |
| Context pre-loaded in first message | Cuts API calls from ~5 to ~2 per run | Agent can't re-query for live updates |
| Gemini free tier (gemini-2.0-flash) | No cost | 1,500 requests/day limit |
| Mocked tests for agent | No API key needed in CI | Tests verify logic, not live model behaviour |

## Testing Summary

**24 tests total — all passing.**

- `tests/test_pawpal.py` (17 tests) — covers sorting, recurrence, and conflict detection in the scheduler
- `tests/test_agent.py` (7 tests) — covers the agent loop using a mocked Gemini client: conflict resolution, clean-schedule no-op, invalid hour rejection, unknown task rejection, log output, and max-iteration cutoff

What worked: mocking the Gemini client made agent tests fast, reliable, and runnable without a key. What didn't: the free-tier daily quota runs out quickly during active testing. What I learned: separating the agent's proposal step from the apply step made both testing and the UI much cleaner.

## Reflection

Building the AI agent taught me that AI reliability isn't just about the model — it's about the structure around it. Giving the agent specific tools and a clear workflow (plan → act → check) produced far more consistent results than open-ended prompting. The human review step was the most important design decision: it meant a bad AI output could never silently break the schedule. I also learned that testing AI with mocks proves the *logic* is sound, but you still need a real API call at least once to confirm the model actually follows your instructions.

 ## Walk-through Link

 https://www.loom.com/share/0151f1ceb7604c379cdb530fed3e2356
 