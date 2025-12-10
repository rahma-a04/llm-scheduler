"""Google Calendar integration with OAuth authentication."""

import json
from typing import List, Optional
from datetime import datetime
from streamlit_oauth import OAuth2Component
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.models import CalendarEvent


class CalendarService:
    """Service for Google Calendar operations with OAuth authentication."""

    SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
    AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(self, credentials_path: str = "../credentials.json"):
        """
        Initialize CalendarService with OAuth credentials.

        Args:
            credentials_path: Path to Google OAuth credentials JSON file
        """
        self.credentials_path = credentials_path
        self._load_credentials()

    def _load_credentials(self):
        """Load OAuth client credentials from JSON file."""
        try:
            with open(self.credentials_path, 'r') as f:
                creds_data = json.load(f)
                # Handle both "installed" and "web" credential types
                if "installed" in creds_data:
                    creds = creds_data["installed"]
                elif "web" in creds_data:
                    creds = creds_data["web"]
                else:
                    raise ValueError("Invalid credentials.json format")

                self.client_id = creds["client_id"]
                self.client_secret = creds["client_secret"]

                # Use localhost:8501 for Streamlit
                self.redirect_uri = "http://localhost:8501"
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Credentials file not found at {self.credentials_path}. "
                "Please download it from Google Cloud Console."
            )
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid credentials file format: {e}")

    def get_oauth_component(self) -> OAuth2Component:
        """
        Create and return OAuth2Component for authentication flow.

        Returns:
            OAuth2Component configured for Google Calendar
        """
        return OAuth2Component(
            client_id=self.client_id,
            client_secret=self.client_secret,
            authorize_endpoint=self.AUTHORIZE_ENDPOINT,
            token_endpoint=self.TOKEN_ENDPOINT,
            refresh_token_endpoint=self.TOKEN_ENDPOINT,
        )

    def _get_calendar_service(self, token: dict):
        """
        Build Google Calendar API service from OAuth token.

        Args:
            token: OAuth token dictionary with access_token

        Returns:
            Google Calendar API service instance
        """
        creds = Credentials(
            token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_uri=self.TOKEN_ENDPOINT,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES
        )
        return build("calendar", "v3", credentials=creds)

    def create_events(
        self,
        events: List[CalendarEvent],
        token: dict,
        calendar_id: str = "primary"
    ) -> tuple[bool, str]:
        """
        Create events in Google Calendar.

        Args:
            events: List of CalendarEvent objects to create
            token: OAuth token from session state
            calendar_id: Calendar ID (default: "primary")

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not token:
            return False, "Not authenticated. Please connect Google Calendar first."

        try:
            service = self._get_calendar_service(token)
            created_count = 0

            for event in events:
                event_body = {
                    "summary": event.title,
                    "description": event.description or "",
                    "start": {
                        "dateTime": event.start.isoformat(),
                        "timeZone": "America/New_York",
                    },
                    "end": {
                        "dateTime": event.end.isoformat(),
                        "timeZone": "America/New_York",
                    },
                }

                service.events().insert(
                    calendarId=calendar_id,
                    body=event_body
                ).execute()
                created_count += 1

            return True, f"Successfully created {created_count} event(s) in Google Calendar!"

        except HttpError as e:
            error_msg = f"Google Calendar API error: {e.reason}"
            if e.resp.status == 401:
                error_msg = "Authentication expired. Please reconnect Google Calendar."
            elif e.resp.status == 403:
                error_msg = "Permission denied. Please ensure Calendar API is enabled."
            elif e.resp.status == 429:
                error_msg = "Rate limit exceeded. Please try again later."
            return False, error_msg

        except Exception as e:
            return False, f"Error creating events: {str(e)}"

    def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        token: dict,
        calendar_id: str = "primary"
    ) -> tuple[Optional[List[CalendarEvent]], Optional[str]]:
        """
        Fetch events from Google Calendar.

        Args:
            start_date: Start of time range
            end_date: End of time range
            token: OAuth token from session state
            calendar_id: Calendar ID (default: "primary")

        Returns:
            Tuple of (events: List[CalendarEvent] or None, error_message: str or None)
        """
        if not token:
            return None, "Not authenticated. Please connect Google Calendar first."

        try:
            service = self._get_calendar_service(token)

            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat() + "Z",
                timeMax=end_date.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = []
            for item in events_result.get("items", []):
                # Skip all-day events
                if "dateTime" not in item.get("start", {}):
                    continue

                events.append(CalendarEvent(
                    title=item.get("summary", "Untitled"),
                    start=datetime.fromisoformat(
                        item["start"]["dateTime"].replace("Z", "+00:00")
                    ),
                    end=datetime.fromisoformat(
                        item["end"]["dateTime"].replace("Z", "+00:00")
                    ),
                    description=item.get("description"),
                    event_id=item.get("id")
                ))

            return events, None

        except HttpError as e:
            error_msg = f"Google Calendar API error: {e.reason}"
            if e.resp.status == 401:
                error_msg = "Authentication expired. Please reconnect Google Calendar."
            return None, error_msg

        except Exception as e:
            return None, f"Error fetching events: {str(e)}"
