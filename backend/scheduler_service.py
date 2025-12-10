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

# The scope defines what your app can access (here, read/write Calendar)
SCOPES = ["https://www.googleapis.com/auth/calendar"]

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
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
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
        "You are an intelligent scheduling assistant." 
        "Your goal is to integrate a new academic task into a student's weekly calendar."
        "You must respect Naji's working hours, breaks, and existing events, while balancing workload across days when available." 
        "If the task is short, you may assign it in one block; if long, split it intelligently across free time before the deadline."
        "Return the final schedule in JSON format that follows Google Calendar’s event schema."
    )

    user_prompt = f"""
    Here is user's current calendar and the new task to be scheduled:
    {json.dumps(payload, indent=2)}

    Please return a JSON array of **new events** to be added to the Google Calendar and only the JSON array 
    with no addional text beyond it as it will be parsed directly to Google Calendar.
    Each event should include: title, start (ISO 8601), end (ISO 8601), and description.
    Ensure all times are within user's working hours, and no overlap occurs.
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

