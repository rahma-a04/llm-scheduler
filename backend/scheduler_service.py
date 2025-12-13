"""Scheduling algorithms - baseline and LLM-based schedulers."""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os.path
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from openai import OpenAI
import json
import re
import os
from typing import List

from backend.models import Task, CalendarEvent, UserPreferences, Schedule

# Scope for Google Calendar API access (read/write permissions)
SCOPES = ["https://www.googleapis.com/auth/calendar"]


# ==================== LEGACY STANDALONE FUNCTIONS ====================
# Kept for backward compatibility with existing code

def get_credentials():
    """Load or create valid Google API credentials."""
    creds = None

    # token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no valid credentials, do the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("../credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for next time
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def fetch_calendar_events(creds: Credentials, calendar_id="primary"):
    """Fetch upcoming events from Google Calendar for the next 7 days."""
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    one_week_later = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        timeMax=one_week_later,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    schedule = []
    for event in events:
        schedule.append({
            "title": event.get("summary", "Untitled Event"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "end": event["end"].get("dateTime", event["end"].get("date")),
        })
    return schedule

def build_chatgpt_payload(user_info, schedule, new_task):
    """Combine user info, current schedule, and new task into a structured payload."""
    payload = {
        "user_profile": user_info,
        "current_schedule": schedule,
        "new_task": new_task
    }
    return payload

def call_chatgpt_scheduler(payload, openai_api_key):
    """Send scheduling data to ChatGPT and return the new events."""

    # Create the OpenAI client with the provided key
    client = OpenAI(api_key=openai_api_key)

    system_prompt = (
        f"""
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
        - If the scehule seems pretty full for a specific day with prior tasks and you have more availibility withing the next days, try to assign block for next days rather than the day that filled up with stuff.

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
    )

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

    # Make the API call
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4
    )

    result_text = response.choices[0].message.content.strip()

    # 🧹 Remove markdown formatting like ```json ... ```
    cleaned = re.sub(r"^```(?:json)?|```$", "", result_text.strip(), flags=re.MULTILINE).strip()

    try:
        scheduled_events = json.loads(cleaned)
        return scheduled_events
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed:", e)
        print("Raw cleaned text:", cleaned)
        return []

def push_events_to_google_calendar(creds: Credentials, events, calendar_id="primary"):
    """
    Pushes a list of events (from ChatGPT's response) to the user's Google Calendar.

    Args:
        creds (Credentials): Authorized Google API credentials.
        events (list): List of event dicts with keys: title, start, end, description.
        calendar_id (str): Target calendar (default = "primary").
    """
    service = build("calendar", "v3", credentials=creds)

    for event in events:
        try:
            new_event = {
                "summary": event.get("title", "Untitled Event"),
                "description": event.get("description", ""),
                "start": {"dateTime": event["start"], "timeZone": "America/New_York"},
                "end": {"dateTime": event["end"], "timeZone": "America/New_York"},
            }

            created_event = service.events().insert(calendarId=calendar_id, body=new_event).execute()
            print(f"✅ Added event: {created_event.get('summary')} ({created_event.get('start').get('dateTime')})")

        except Exception as e:
            print(f"❌ Failed to add event '{event.get('title', 'Untitled Event')}': {e}")

def baseline_schedule(existing_events, new_task, user_info, buffer_minutes=15):
    """
    Algorithm to create a schedule based on a deterministic (greedy) algorithm.

    Returns: List of new events to be scheduled.
    """

    # user prefs
    work_start = user_info["working_hours"]["start"]  # "09:00"
    work_end = user_info["working_hours"]["end"]      # "22:00"
    break_times = user_info.get("break_times", [])
    max_daily_hours = user_info.get("max_daily_workload_hours", 24)

    ws_h, ws_m = map(int, work_start.split(":"))
    we_h, we_m = map(int, work_end.split(":"))

    # task info
    title = new_task["title"]
    hours_needed = float(new_task["estimated_duration_hours"])
    deadline = datetime.fromisoformat(new_task["deadline"])
    can_split = bool(new_task.get("can_be_split", True))
    priority = new_task.get("priority", "medium")

    PRIORITY_WEIGHTS = {"low": 0.8, "medium": 1.0, "high": 1.3}
    hours_needed *= PRIORITY_WEIGHTS.get(priority, 1.0)

    # build busy schedule
    busy = {}
    for ev in existing_events:
        s = datetime.fromisoformat(ev["start"])
        e = datetime.fromisoformat(ev["end"])
        day = s.date()
        busy.setdefault(day, []).append((s, e))

    # add break times to busy schedule
    today = datetime.now().date()
    last_day = deadline.date()

    while today <= last_day:
        for br in break_times:
            bstart = datetime.fromisoformat(f"{today}T{br['start']}:00")
            bend   = datetime.fromisoformat(f"{today}T{br['end']}:00")
            busy.setdefault(today, []).append((bstart, bend))
        today += timedelta(days=1)

    # determine available days for task
    all_days = []
    current = datetime.now().date()
    while current <= deadline.date():
        all_days.append(current)
        current += timedelta(days=1)

    # daily target
    hrs_per_day = hours_needed / len(all_days)
    new_events = []

    # schedule
    for day in all_days:
        if hours_needed <= 0:
            break

        start_work = datetime(day.year, day.month, day.day, ws_h, ws_m)
        end_work = datetime(day.year, day.month, day.day, we_h, we_m)

        free_blocks = [(start_work, end_work)]

        # busy times and buffers
        if day in busy:
            for (bs, be) in sorted(busy[day]):
                adj_start = bs - timedelta(minutes=buffer_minutes)
                adj_end   = be + timedelta(minutes=buffer_minutes)

                temp = []
                for (fs, fe) in free_blocks:
                    if adj_end <= fs or adj_start >= fe:
                        temp.append((fs, fe))
                    else:
                        if fs < adj_start:
                            temp.append((fs, adj_start))
                        if adj_end < fe:
                            temp.append((adj_end, fe))
                free_blocks = temp

        # working times
        today_target = min(hrs_per_day, hours_needed, max_daily_hours)
        minutes_needed = int(today_target * 60)

        for (fs, fe) in free_blocks:
            free_minutes = int((fe - fs).total_seconds() / 60)
            if free_minutes < 30:
                continue

            duration = min(free_minutes, minutes_needed)
            if duration < 30:
                continue

            block_end = fs + timedelta(minutes=duration)
            new_events.append({
                "title": title,
                "start": fs.isoformat(),
                "end": block_end.isoformat(),
                "description": f"{title} (Priority {priority})"
            })
            minutes_needed -= duration
            hours_needed -= duration / 60

            if minutes_needed <= 0 or not can_split:
                break

    return new_events


# ==================== NEW CLASS-BASED ARCHITECTURE ====================

class BaselineScheduler:
    """Greedy algorithm scheduler - deterministic baseline."""

    def generate_schedule(
        self,
        tasks: List[Task],
        existing_events: List[CalendarEvent],
        preferences: UserPreferences
    ) -> Schedule:
        """Generate schedule using greedy algorithm."""
        # Sort tasks by deadline FIRST (earlier deadlines first), then by priority
        # This ensures urgent tasks are scheduled before less urgent ones
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (t.deadline, t.priority.value)
        )

        all_events = []
        for task in sorted_tasks:
            events = self._schedule_task(
                task,
                existing_events + all_events,
                preferences
            )
            all_events.extend(events)

        return Schedule(events=all_events)

    def _schedule_task(
        self,
        task: Task,
        busy_events: List[CalendarEvent],
        preferences: UserPreferences
    ) -> List[CalendarEvent]:
        """Schedule a single task greedily."""
        events = []

        # Build busy schedule by day (convert to naive datetimes for comparison)
        busy_by_day = {}
        for event in busy_events:
            # Strip timezone info to avoid comparison issues
            start_naive = event.start.replace(tzinfo=None) if event.start.tzinfo else event.start
            end_naive = event.end.replace(tzinfo=None) if event.end.tzinfo else event.end

            day = start_naive.date()
            buffer = timedelta(minutes=preferences.buffer_minutes)
            start_with_buffer = start_naive - buffer
            end_with_buffer = end_naive + buffer
            busy_by_day.setdefault(day, []).append((start_with_buffer, end_with_buffer))

        # Calculate available days
        start_date = datetime.now().date()
        deadline_date = task.deadline.date()
        days = []
        current_date = start_date
        while current_date <= deadline_date:
            days.append(current_date)
            current_date += timedelta(days=1)

        if not days:
            return events

        # Greedy scheduling: schedule as much as possible each day until task is complete
        # This is the standard greedy approach (not even distribution)
        hours_remaining = task.estimated_hours
        MIN_BLOCK_HOURS = 0.5  # Minimum 30 minutes per block

        for day in days:
            if hours_remaining <= 0:
                break

            # Get free blocks for this day
            work_start = datetime.combine(day, preferences.working_hours.start)
            work_end = datetime.combine(day, preferences.working_hours.end)

            free_blocks = self._get_free_blocks(
                work_start,
                work_end,
                busy_by_day.get(day, [])
            )

            daily_scheduled = 0.0

            for start, end in free_blocks:
                if hours_remaining <= 0 or daily_scheduled >= preferences.max_daily_hours:
                    break

                block_hours = (end - start).total_seconds() / 3600
                # Schedule as much as possible in this block (up to remaining hours and daily limit)
                available = min(block_hours, hours_remaining, preferences.max_daily_hours - daily_scheduled)

                # Only schedule if block meets minimum duration
                if available >= MIN_BLOCK_HOURS:
                    event_end = start + timedelta(hours=available)
                    events.append(CalendarEvent(
                        title=task.name,
                        start=start,
                        end=event_end,
                        description=f"{task.subject} (Priority: {task.priority.value})"
                    ))

                    daily_scheduled += available
                    hours_remaining -= available

                    if not task.can_be_split:
                        break

        return events

    def _get_free_blocks(
        self,
        work_start: datetime,
        work_end: datetime,
        busy_times: List[tuple[datetime, datetime]]
    ) -> List[tuple[datetime, datetime]]:
        """Calculate free time blocks for a working window."""
        free_blocks = [(work_start, work_end)]

        for busy_start, busy_end in sorted(busy_times):
            temp = []
            for fs, fe in free_blocks:
                if busy_end <= fs or busy_start >= fe:
                    temp.append((fs, fe))
                else:
                    if fs < busy_start:
                        temp.append((fs, busy_start))
                    if busy_end < fe:
                        temp.append((busy_end, fe))
            free_blocks = temp

        return free_blocks


class LLMScheduler:
    """LLM-based scheduler using OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_schedule(
        self,
        tasks: List[Task],
        existing_events: List[CalendarEvent],
        preferences: UserPreferences
    ) -> Schedule:
        """Generate schedule using LLM."""
        all_events = []

        for task in tasks:
            events = self._schedule_task_with_llm(
                task,
                existing_events + all_events,
                preferences
            )
            all_events.extend(events)

        return Schedule(events=all_events)

    def _schedule_task_with_llm(
        self,
        task: Task,
        existing_events: List[CalendarEvent],
        preferences: UserPreferences
    ) -> List[CalendarEvent]:
        """Use LLM to schedule a single task."""

        system_prompt = (
            """
            You are an intelligent scheduling assistant designed to create an optimal study-oriented schedule.

            You are given:
            1) The user's current Google Calendar events (in the "existing_events" array)
            2) One or more new tasks that may be distributable across multiple time blocks
            3) The user's stated preferences (working hours, weekend preferences, and study habits)

            Your objective is to generate an optimal schedule by returning ONLY a JSON array of **new events** to be added to Google Calendar.

            ━━━━━━━━━━━━━━━━━━━━━━
            📌 Scheduling Rules & Logic
            ━━━━━━━━━━━━━━━━━━━━━━

            GENERAL RULES:
            - Do NOT modify or delete existing calendar events.
            - CRITICAL CONSTRAINT: Do NOT overlap new events with existing events or with each other. All events must be scheduled in SEPARATE time blocks.
            - All events should respect the user's preferred working hours whenever possible.
            - This system is primarily for STUDENTS, so do NOT assume a strict 9–5 work schedule.
            - Prefer spreading work to avoid burnout unless the task logically requires focus continuity.
            - Make sure the tasks are not assigned to times that has already past, make sure they are assigned to future times/days.
            - If the preferences object contains 'study_habits' with user-provided information, carefully consider these habits when scheduling.
              For example, if the user says "I focus best in the mornings", prioritize scheduling important tasks in morning hours.
              If they mention "I prefer shorter study sessions", favor splitting tasks into smaller blocks.

            TASK DISTRIBUTION:
            - If a task is distributable, intelligently split it into multiple sessions.
            - For instance, if a task takes 8 hours and is due in 4 days, distribute it evenly 2 hours per day for the next for days if possible.
            - Decide whether sessions should be:
            • spread evenly across multiple days, OR
            • grouped closer together
            based on task type (e.g., exam prep vs short assignment), urgency, and workload.
            - Balance consistency and rest (avoid scheduling too many long sessions on one day).
            - If the scehule seems pretty full for a specific day with prior tasks and you have more availibility withing the next days, try to assign block for next days rather than the day that filled up with stuff.

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
        )

        payload = {
            "current_datetime": datetime.now().isoformat(),
            "task": {
                "name": task.name,
                "subject": task.subject,
                "estimated_hours": task.estimated_hours,
                "deadline": task.deadline.isoformat(),
                "priority": task.priority.value,
                "can_be_split": task.can_be_split
            },
            "existing_events": [
                {
                    "title": e.title,
                    "start": e.start.isoformat(),
                    "end": e.end.isoformat()
                }
                for e in existing_events
            ],
            "preferences": {
                "working_hours": {
                    "start": preferences.working_hours.start.isoformat(),
                    "end": preferences.working_hours.end.isoformat()
                },
                "max_daily_hours": preferences.max_daily_hours,
                "buffer_minutes": preferences.buffer_minutes,
                "study_habits": preferences.study_habits if preferences.study_habits else None
            }
        }

        user_prompt = f"""
        Here is user's current calendar and the new task to be scheduled:
        {json.dumps(payload, indent=2)}

        IMPORTANT: The current_datetime field shows the current time. ALL scheduled events MUST have start times AFTER this datetime.
        Do NOT schedule any events in the past.

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

        • CRITICAL: All event start times must be AFTER current_datetime ({datetime.now().isoformat()}). Never schedule events in the past.

        • Output must be ONLY the JSON array of new events with valid ISO timestamps.
        """

        # Make the API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4
        )

        result_text = response.choices[0].message.content.strip()

        # Clean markdown formatting
        cleaned = re.sub(
            r"^```(?:json)?|```$",
            "",
            result_text.strip(),
            flags=re.MULTILINE
        ).strip()

        try:
            events_data = json.loads(cleaned)
            return self._parse_events(events_data)
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Raw cleaned text: {cleaned}")
            return []

    def _parse_events(self, events_data: List[dict]) -> List[CalendarEvent]:
        """Parse JSON events into CalendarEvent objects."""
        events = []
        current_time = datetime.now()

        for data in events_data:
            try:
                start_time = datetime.fromisoformat(data["start"])
                end_time = datetime.fromisoformat(data["end"])

                # Skip events scheduled in the past
                # Handle timezone-aware vs naive datetime comparison
                start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
                if start_time_naive < current_time:
                    print(f"Warning: Skipping event '{data.get('title', '')}' scheduled in the past (start: {start_time})")
                    continue

                events.append(CalendarEvent(
                    title=data.get("title", ""),
                    start=start_time,
                    end=end_time,
                    description=data.get("description", "")
                ))
            except (KeyError, ValueError) as e:
                print(f"Error parsing event: {e}")
                continue
        return events
