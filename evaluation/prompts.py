"""
Prompting strategies for LLM-based scheduling evaluation.

This module defines four different prompting strategies to evaluate:
1. Zero-shot
2. Few-shot
3. Chain-of-Thought (CoT)
4. Constraint-first
"""

import json
from typing import Dict, Any


class PromptStrategy:
    """Base class for prompting strategies."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        """Build system and user prompts for this strategy.

        Args:
            payload: Dictionary containing preferences, existing_events, and new_tasks

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        raise NotImplementedError


class ZeroShotStrategy(PromptStrategy):
    """Zero-shot prompting strategy."""

    def __init__(self):
        super().__init__(
            name="zero_shot",
            description="Direct zero-shot prompting with clear instructions"
        )

    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
        You are an intelligent scheduling assistant designed to create an optimal study-oriented schedule.

        You are given:
        1) The user's current Google Calendar events
        2) One or more new tasks that may be distributable across multiple time blocks
        3) The user's stated preferences (working hours, weekend preferences, and any notes in the task description)

        Your objective is to generate an optimal schedule by returning ONLY a JSON array of **new events** to be added to Google Calendar.

        ━━━━━━━━━━━━━━━━━━━━━━
        📌 Scheduling Rules & Logic
        ━━━━━━━━━━━━━━━━━━━━━━

        GENERAL RULES:

        - Only schedule tasks from this Sunday Dec 14 - 2025 onward not before.
        - Do NOT modify or delete existing calendar events.
        - New events MUST NOT overlap with existing events or with each other.
        - All events should respect the user's preferred working hours whenever possible.
        - This system is primarily for STUDENTS, so do NOT assume a strict 9–5 work schedule.
        - Prefer spreading work to avoid burnout unless the task logically requires focus continuity.
        - Make sure the tasks are not assigned to times that has already past, make sure they are assigned to future times/days.


        TASK DISTRIBUTION:
        - If a task is distributable, intelligently split it into multiple sessions.
        - For instance, if a task takes 8 hours and is due in 4 days, distribute it evenly 2 hours per day for the next for days if possible.
        - Decide whether sessions should be:
        • spread evenly across multiple days, OR
        • grouped closer together
        based on task type (e.g., exam prep vs short assignment), urgency, and workload.
        - Balance consistency and rest (avoid scheduling too many long sessions on one day).
        - If the schedule seems pretty full for a specific day with prior tasks and you have more availability within the next few days, try to assign a block for next days rather than the day that is filled up with stuff.

        WEEKEND LOGIC:
        - If the user explicitly states they do NOT want to work on weekends (in preferences or task description), do NOT schedule any tasks on weekends.
        - If the user has NOT specified a restriction on weekends, you MAY use weekends as valid scheduling days if it improves task distribution.

        WORKING HOURS OVERRIDES:
        - ONLY schedule tasks outside preferred working hours if:
        • there is absolutely no feasible way to place all required sessions within preferences.
        - If you must schedule outside preferred hours:
        • minimize how far outside those hours the event occurs.
        • prefer earlier evenings over late nights.

        TIME BLOCK STRATEGY:
        - Prefer realistic study blocks (e.g., 30–120 minutes).
        - Include short breaks implicitly by avoiding back-to-back long blocks.
        - Do not overschedule a single day unless unavoidable.
        """

        user_prompt = f"""
    Here is user's current calendar and the new task to be scheduled:
    {json.dumps(payload, indent=2)}

    Please return a JSON array of **new events** to be added to the Google Calendar and only the JSON array
    with no additional text beyond it, as it will be parsed directly to Google Calendar.

    Each event should include:
    - title
    - start (ISO 8601)
    - end (ISO 8601)
    - description

    Requirements you must follow when generating the schedule:

    • Ensure all tasks are distributed intelligently, splitting them when needed and placing them in the best free time slots relative to the user's schedule.

    • If the user has indicated they do NOT want to work on weekends, do not schedule any weekend events.
    If the user has not expressed a preference against weekends, weekends may and should be used when helpful.

    • Use reasoning to determine whether to spread the task over broader days or to place sessions on consecutive days.

    • If possibly prioritize assigning portions of task over multiple days rather than multiple portions in only one day.

    • Because this system is for students, do NOT assume a 9–5 schedule. Use the user's working-hour preferences directly.

    • Tasks should only be placed outside working-hour preferences if there is absolutely no way to fit all required time within preferred hours.

    • Ensure no event overlaps with existing calendar events or other newly created events.

    • Make sure the tasks are not assigned to times that has already past, make sure they are assigned to future times/days.

    • Output must be ONLY the JSON array of new events with valid ISO timestamps.
    """

        return system_prompt, user_prompt


class FewShotStrategy(PromptStrategy):
    """Few-shot prompting strategy with examples."""

    def __init__(self):
        super().__init__(
            name="few_shot",
            description="Few-shot learning with example input-output pairs"
        )

    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
You are an intelligent scheduling assistant for students.
Your goal is to integrate new academic tasks into the user's existing weekly calendar while respecting working-hour preferences, weekend rules, deadlines, max daily hours, and the constraints described below.

Core constraints you must follow:
- Only schedule tasks from this Sunday Dec 14 - 2025 onward not before.
- Do NOT modify or delete existing calendar events.
- New events MUST NOT overlap with existing events or with each other.
- Work must occur within the user's study/study windows whenever possible.
- If the user states they do not work on weekends, do NOT schedule events on Saturday or Sunday.
- Daily work must not exceed max_daily_hours.
- This system is for STUDENTS; do NOT assume a 9–5 schedule. Use the provided preferences directly.
- Tasks must not be assigned to times that have already passed; all new events must be in the future.
- Long tasks should be divided into logical study blocks (typically 30–120 minutes), and workload should be distributed in a student-friendly way across days.

Below are examples showing how to transform:
(1) user preferences
(2) existing Google Calendar events
(3) new tasks
into
(4) a JSON array of scheduled events.

EXAMPLE 1 — INPUT
{
  "preferences": {
    "study_windows": "Mon–Fri 10:00–18:00",
    "max_daily_hours": 5,
    "break_pattern": "10 min break every hour",
    "additional_notes": "No weekends"
  },
  "existing_events": [
    {
      "summary": "Lecture",
      "start": "2025-02-10T10:00:00-05:00",
      "end":   "2025-02-10T11:30:00-05:00",
      "description": "CS class"
    }
  ],
  "new_tasks": [
    {
      "id": 1,
      "name": "PS1",
      "subject": "Math",
      "estimated_hours": 3,
      "deadline": "2025-02-13",
      "priority": "high"
    }
  ]
}

EXAMPLE 1 — OUTPUT (JSON ONLY)
[
  {
    "title": "Work on PS1",
    "start": "2025-02-11T14:00:00-05:00",
    "end":   "2025-02-11T16:00:00-05:00",
    "description": "Task: PS1 (Math)"
  },
  {
    "title": "Work on PS1",
    "start": "2025-02-12T15:00:00-05:00",
    "end":   "2025-02-12T16:00:00-05:00",
    "description": "Task: PS1 (Math)"
  }
]

EXAMPLE 2 — INPUT
{
  "preferences": {
    "study_windows": "Daily 12:00–22:00",
    "max_daily_hours": 6,
    "break_pattern": "",
    "additional_notes": ""
  },
  "existing_events": [],
  "new_tasks": [
    {
      "id": 4,
      "name": "Essay Draft",
      "subject": "Writing",
      "estimated_hours": 4,
      "deadline": "2025-02-09",
      "priority": "medium"
    }
  ]
}

EXAMPLE 2 — OUTPUT
[
  {
    "title": "Work on Essay Draft",
    "start": "2025-02-07T18:00:00-05:00",
    "end":   "2025-02-07T20:00:00-05:00",
    "description": "Task: Essay Draft (Writing)"
  },
  {
    "title": "Work on Essay Draft",
    "start": "2025-02-08T17:00:00-05:00",
    "end":   "2025-02-08T19:00:00-05:00",
    "description": "Task: Essay Draft (Writing)"
  }
]

Follow the same style, constraints, and logic when generating schedules for new inputs.
"""

        user_prompt = f"""
Here is the user's current calendar + preferences + new tasks:
{json.dumps(payload, indent=2)}

Return ONLY a JSON array of newly scheduled events to be added to Google Calendar.

Each event MUST include:
- "title"
- "start" (ISO 8601)
- "end"   (ISO 8601)
- "description"

No explanations. No comments. Only the JSON array.
"""

        return system_prompt, user_prompt


class ChainOfThoughtStrategy(PromptStrategy):
    """Chain-of-Thought prompting strategy."""

    def __init__(self):
        super().__init__(
            name="chain_of_thought",
            description="Step-by-step reasoning (internal) before generating output"
        )

    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
You are an intelligent scheduling assistant.
Your task is to schedule new academic tasks into a student's weekly calendar while respecting all constraints.

You are given:
1) The user's current Google Calendar events
2) One or more new tasks that may be distributable across multiple time blocks
3) The user's stated preferences (study windows / working hours, weekend preferences, max_daily_hours, and any additional notes)

First, think step-by-step about:
- how much time each task requires,
- where free blocks exist,
- how to distribute workload across days,
- whether weekends are allowed,
- how to avoid overlap,
- how to stay within the user's working-hours,
- whether any tasks require scheduling outside preferences due to impossibility,
- and how to split tasks efficiently while avoiding burnout.

Do all of this reasoning INTERNALLY. Do NOT include the reasoning or any explanation in your final answer.

You must then output ONLY the final JSON schedule, as a JSON array of new events to be added to Google Calendar.

━━━━━━━━━━━━━━━━━━━━━━
📌 Constraints & Scheduling Rules
━━━━━━━━━━━━━━━━━━━━━━

Hard constraints (must always be satisfied unless explicitly noted otherwise):
• Only schedule tasks from this Sunday Dec 14 - 2025 onward not before.
• No overlapping events (new events must not overlap with each other or existing events).
• Stay within the user's study windows / working hours unless it is absolutely impossible to fit all required time before deadlines.
• Respect "no weekends" if present in additional notes or task descriptions.
• Respect max_daily_hours when allocating work per day.
• Only schedule tasks in the future: do NOT assign events to times that have already passed.
• This system is for STUDENTS: do NOT assume a 9–5 schedule; instead, use the provided preferences directly.
• If you must go outside preferred working hours because it is otherwise impossible to finish on time, minimize the violation and prefer earlier evenings over very late-night blocks.

Task distribution guidelines:
• Distribute multi-day tasks intelligently across available days.
• Decide whether to spread work across multiple days or cluster it on consecutive days based on urgency, deadlines, and existing workload.
• Prefer realistic study blocks (e.g., 30–120 minutes) and avoid overscheduling a single day when future days are available.
• If a day is already quite full and there is room on later days before the deadline, prefer scheduling on the later days instead of overloading the busy day.
• When possible, prioritize assigning portions of a task across multiple days rather than packing many blocks of the same task into one day.

Output contract:
• After reasoning, you must output ONLY a JSON array of new events.
• Each event must have: "title", "start", "end", and "description".
• "start" and "end" must be valid ISO 8601 timestamps (including offset).
• Do NOT include any explanations, comments, or extra keys in the response.
"""

        user_prompt = f"""
Here is the student's full input (current calendar, preferences, and new tasks):
{json.dumps(payload, indent=2)}

NOW produce ONLY a JSON array of new scheduled events to be added to Google Calendar, following all constraints above.

Each event MUST include:
- "title"
- "start" (ISO 8601)
- "end"   (ISO 8601)
- "description"

Do NOT output any explanations or reasoning. Return ONLY the JSON array.
"""

        return system_prompt, user_prompt


class ConstraintFirstStrategy(PromptStrategy):
    """Constraint-first prompting strategy."""

    def __init__(self):
        super().__init__(
            name="constraint_first",
            description="Explicit constraint enumeration before scheduling"
        )

    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
You are an intelligent scheduling assistant.

Before generating the schedule, you MUST obey the following constraints in strict priority order:

1. Deadlines must be met.
2. No scheduled event may overlap with existing calendar events or other new events.
3. Work must occur within the user's study windows unless it is absolutely impossible to fit all required time before the deadline.
4. If the user states they do not work on weekends, no events may be scheduled on Saturday or Sunday.
5. Daily work must not exceed max_daily_hours.
6. Long tasks must be divided into logical blocks.
7. Workload should be distributed in a student-friendly manner (not assuming a 9–5 schedule).
8. Task priority should influence earlier placement when possible.
9. Maintain realistic study blocks (30–120 minutes unless the task clearly requires otherwise).
10. Tasks must not be assigned to times that have already passed; all scheduled events must be in the future relative to the current time and date.
11. Only schedule tasks from this Sunday Dec 14 - 2025 onward not before.

Additional guidelines:
- This system is primarily for STUDENTS, so you must rely on the provided preferences and not assume a standard office schedule.
- If it is absolutely impossible to satisfy all constraints simultaneously, you may only relax constraint #3 (study windows) and constraint #9 (block length), and only as much as necessary to meet deadlines.
- When relaxing constraints, minimize violations (e.g., slightly outside study window is better than far outside; modestly longer blocks are better than extremely long ones).

After applying ALL constraints, create the best possible schedule that:
- Meets deadlines when feasible,
- Minimizes overload on any single day when future days are available before the deadline,
- Distributes multi-day tasks sensibly across the available time.

Required output contract:
- Return only a JSON array of new events to be added to Google Calendar.
- Each event must include:
  - "title"
  - "start" (ISO 8601 timestamp, including offset)
  - "end"   (ISO 8601 timestamp, including offset)
  - "description"
- Do NOT modify or delete any existing events.
- Do NOT return any explanations, reasoning, or extra fields.
"""

        user_prompt = f"""
Here is the user's full scheduling input (preferences, existing events, and new tasks):
{json.dumps(payload, indent=2)}

Return ONLY a JSON array of new events that satisfy the constraints described in the system prompt.

Each event MUST include:
- "title"
- "start" (ISO 8601)
- "end"   (ISO 8601)
- "description"

No explanations. No comments. Only the JSON array.
"""

        return system_prompt, user_prompt


# Strategy registry
STRATEGIES = {
    'zero_shot': ZeroShotStrategy(),
    'few_shot': FewShotStrategy(),
    'chain_of_thought': ChainOfThoughtStrategy(),
    'constraint_first': ConstraintFirstStrategy()
}


def get_strategy(name: str) -> PromptStrategy:
    """Get a prompting strategy by name.

    Args:
        name: Strategy name (zero_shot, few_shot, chain_of_thought, constraint_first)

    Returns:
        PromptStrategy instance

    Raises:
        ValueError: If strategy name is not recognized
    """
    if name not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}"
        )
    return STRATEGIES[name]


def list_strategies() -> Dict[str, str]:
    """List all available strategies with descriptions.

    Returns:
        Dictionary mapping strategy names to descriptions
    """
    return {name: strategy.description for name, strategy in STRATEGIES.items()}
