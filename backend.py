from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os.path
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from openai import OpenAI
import json
import re
from dotenv import load_dotenv
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
