"""Main Streamlit application for AI Task Planner."""

import streamlit as st
from datetime import datetime, time, timedelta
import json
import os
import sys

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.models import Priority, WorkingHours, UserPreferences, CalendarEvent
from backend.calendar_service import CalendarService
from backend.scheduler_service import LLMScheduler, BaselineScheduler
from backend.task_manager import TaskManager
from backend.config import get_settings

# ==================== SETUP ====================
st.set_page_config(page_title="AI Task Planner", page_icon="📅", layout="wide")

# Initialize settings
settings = get_settings()

# Initialize session state
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "schedule" not in st.session_state:
    st.session_state.schedule = None
if "preferences" not in st.session_state:
    st.session_state.preferences = {
        'work_start': time(9, 0),
        'work_end': time(22, 0),
        'max_daily_hours': settings.default_max_daily_hours,
        'buffer_minutes': settings.default_buffer_minutes
    }
if 'google_token' not in st.session_state:
    st.session_state.google_token = None
if 'calendar_service' not in st.session_state:
    st.session_state.calendar_service = CalendarService(settings.google_credentials_path)
if 'task_manager' not in st.session_state:
    st.session_state.task_manager = TaskManager()

# Get services
calendar_service = st.session_state.calendar_service
task_manager = st.session_state.task_manager

# ==================== UI STYLE ====================
st.markdown(
    """
    <style>
    .main {
        background-color: #f8fafc;
    }
    .stButton>button {
        width: 100%;
    }
    .task-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
        background-color: white;
        margin-bottom: 0.5rem;
    }
    .schedule-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #4f46e5;
        background-color: white;
        margin-bottom: 0.5rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==================== PAGE HEADER ====================
st.title("📅 AI Task Planner")
st.markdown("*Smart scheduling powered by LLM*")
st.divider()

tab1, tab2, tab3 = st.tabs(["📝 Tasks", "⚙️ Preferences", "📆 Schedule"])

# ==================== TAB 1: TASKS ====================
with tab1:
    st.header("Add New Task")

    # Task input form
    col1, col2 = st.columns(2)

    with col1:
        task_name = st.text_input("Task Name *", key="task_name")
        estimated_hours = st.number_input(
            "Estimated Hours *", min_value=0.5, max_value=20.0, step=0.5, key="est_hours"
        )
        priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1, key="priority")

    with col2:
        subject = st.text_input("Subject", value="General", key="subject")
        deadline = st.date_input("Deadline *", min_value=datetime.today(), key="deadline")

    if st.button("➕ Add Task", type="primary"):
        if task_name and estimated_hours and deadline:
            # Add task using TaskManager
            task = task_manager.add_task(
                name=task_name,
                subject=subject,
                estimated_hours=estimated_hours,
                deadline=datetime.combine(deadline, time(23, 59)),
                priority=Priority[priority.upper()]
            )
            st.success(f"✅ Added: {task_name}")
            st.rerun()
        else:
            st.error("Please fill in all required fields (*)")

    st.divider()

    # Display tasks
    st.header(f"Your Tasks ({len(task_manager.get_all_tasks())})")

    tasks = task_manager.get_all_tasks()

    if not tasks:
        st.info("📋 No tasks added yet. Add your first task above!")
    else:
        for idx, task in enumerate(tasks):
            col1, col2 = st.columns([5, 1])

            with col1:
                priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                st.markdown(
                    f"""
                    <div class="task-card">
                        <h4>{priority_emoji[task.priority.value]} {task.name}</h4>
                        <p>📚 {task.subject} | ⏱️ {task.estimated_hours}h | 📅 Due: {task.deadline.strftime("%Y-%m-%d")}</p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

            with col2:
                if st.button("🗑️", key=f"delete_{task.id}"):
                    task_manager.remove_task(task.id)
                    st.rerun()

        st.divider()

        # Generate schedule button using NEW class-based architecture
        button_text = "🚀 Generate AI Schedule" if settings.default_scheduler == "llm" else "🚀 Generate Schedule"

        if st.button(button_text, type="primary", use_container_width=True):
            # Only check API key if using LLM scheduler
            if settings.default_scheduler == "llm" and not settings.openai_api_key:
                st.error("❌ OPENAI_API_KEY is not set. Please add it to your .env file.")
            else:
                spinner_text = "🤖 AI is creating your optimal schedule..." if settings.default_scheduler == "llm" else "📊 Creating your schedule..."
                with st.spinner(spinner_text):
                    try:
                        # Build preferences object
                        preferences = UserPreferences(
                            working_hours=WorkingHours(
                                start=st.session_state.preferences['work_start'],
                                end=st.session_state.preferences['work_end']
                            ),
                            max_daily_hours=st.session_state.preferences['max_daily_hours'],
                            buffer_minutes=st.session_state.preferences['buffer_minutes']
                        )

                        # Fetch existing calendar events if connected
                        existing_events = []
                        if st.session_state.google_token:
                            start_date = datetime.now()
                            end_date = start_date + timedelta(days=7)
                            events_result, error = calendar_service.fetch_events(
                                start_date,
                                end_date,
                                st.session_state.google_token
                            )
                            if events_result:
                                existing_events = events_result
                            elif error:
                                st.warning(f"Could not fetch calendar events: {error}")

                        # Initialize scheduler based on config settings
                        if settings.default_scheduler == "baseline":
                            scheduler = BaselineScheduler()
                            scheduler_name = "Baseline (Greedy)"
                        else:
                            scheduler = LLMScheduler(settings.openai_api_key, settings.llm_model)
                            scheduler_name = "AI (LLM)"

                        # Generate schedule using new class-based API
                        schedule = scheduler.generate_schedule(
                            task_manager.get_all_tasks(),
                            existing_events,
                            preferences
                        )

                        # Save schedule in session
                        st.session_state.schedule = schedule

                        if schedule.events:
                            st.success(f"✅ Schedule generated with {len(schedule.events)} events using {scheduler_name} scheduler!")
                            st.balloons()
                        else:
                            st.warning("⚠️ Scheduler returned no events. Please try again.")

                    except Exception as e:
                        st.error(f"❌ Error while generating schedule: {e}")
                        import traceback
                        st.code(traceback.format_exc())

# ==================== TAB 2: PREFERENCES ====================
with tab2:
    st.header("⚙️ Study Preferences")
    st.markdown("*Configure your study habits and preferences*")

    col1, col2 = st.columns(2)
    with col1:
        work_start = st.time_input("Work Start Time", value=st.session_state.preferences['work_start'])
    with col2:
        work_end = st.time_input("Work End Time", value=st.session_state.preferences['work_end'])

    max_daily_hours = st.slider(
        "Maximum Daily Study Hours",
        min_value=1,
        max_value=12,
        value=st.session_state.preferences['max_daily_hours'],
        help="Maximum hours you want to study per day"
    )

    buffer_minutes = st.number_input(
        "Buffer Time (minutes)",
        min_value=0,
        max_value=60,
        value=st.session_state.preferences['buffer_minutes'],
        help="Time buffer between events"
    )

    if st.button("💾 Save Preferences", type="primary"):
        st.session_state.preferences = {
            'work_start': work_start,
            'work_end': work_end,
            'max_daily_hours': max_daily_hours,
            'buffer_minutes': buffer_minutes
        }
        st.success("✅ Preferences saved!")

    st.info(
        "💡 **Tip:** These preferences help the AI create a personalized schedule that fits your study style and availability."
    )

# ==================== TAB 3: SCHEDULE ====================
with tab3:
    st.header("📆 Your AI-Generated Schedule")

    schedule = st.session_state.schedule

    if not schedule:
        st.info("📋 No schedule generated yet. Add tasks and click 'Generate AI Schedule' to get started!")
    else:
        # Display schedule summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Events", len(schedule.events))
        with col2:
            st.metric("Total Tasks", schedule.total_tasks)
        with col3:
            st.metric("Total Hours", f"{schedule.total_hours:.1f}h")

        # Check for conflicts
        if schedule.has_conflicts():
            st.warning("⚠️ Warning: Schedule has conflicting events!")

        st.divider()
        st.subheader("📋 Scheduled Study Sessions")

        for event in schedule.events:
            st.markdown(
                f"""
                <div class="schedule-card">
                    <h4>{event.title}</h4>
                    <p>📅 {event.start.strftime("%Y-%m-%d")} |
                    ⏰ {event.start.strftime("%H:%M")} - {event.end.strftime("%H:%M")} |
                    ⏱️ {event.duration_hours:.1f}h</p>
                    <p>📝 {event.description}</p>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.divider()

        # Export options
        col1, col2 = st.columns(2)
        with col1:
            # Show connection status for export button
            is_connected = st.session_state.google_token is not None

            if not is_connected:
                st.warning("⚠️ Connect Google Calendar in sidebar to export")

            export_button_disabled = not is_connected

            if st.button(
                "📥 Export to Google Calendar",
                type="primary",
                use_container_width=True,
                disabled=export_button_disabled
            ):
                with st.spinner("Exporting to Google Calendar..."):
                    success, message = calendar_service.create_events(
                        events=schedule.events,
                        token=st.session_state.google_token
                    )
                    if success:
                        st.success(message)
                        st.info("💡 View your calendar at [Google Calendar](https://calendar.google.com)")
                    else:
                        st.error(message)
                        if "expired" in message.lower() or "authentication" in message.lower():
                            st.session_state.google_token = None
                            st.info("Please reconnect Google Calendar in the sidebar and try again.")

        with col2:
            # Convert schedule to JSON-serializable format
            schedule_dict = {
                "events": [
                    {
                        "title": event.title,
                        "start": event.start.isoformat(),
                        "end": event.end.isoformat(),
                        "description": event.description
                    }
                    for event in schedule.events
                ],
                "total_hours": schedule.total_hours,
                "total_tasks": schedule.total_tasks,
                "created_at": schedule.created_at.isoformat()
            }
            json_str = json.dumps(schedule_dict, indent=2)
            st.download_button(
                label="📄 Download as JSON",
                data=json_str,
                file_name="schedule.json",
                mime="application/json",
                use_container_width=True
            )

# ==================== SIDEBAR ====================
with st.sidebar:
    # Google Calendar OAuth Section
    st.header("🔐 Google Calendar")

    oauth_component = calendar_service.get_oauth_component()

    if st.session_state.google_token is None:
        # Not connected - show connect button
        st.info("Connect your Google Calendar to export schedules")
        result = oauth_component.authorize_button(
            name="Connect Google Calendar",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=calendar_service.redirect_uri,
            scope=" ".join(CalendarService.SCOPES),
            key="google_oauth",
            use_container_width=True
        )

        if result and "token" in result:
            st.session_state.google_token = result["token"]
            st.success("✅ Connected to Google Calendar!")
            st.rerun()
    else:
        # Connected - show status and disconnect option
        st.success("✅ Connected to Google Calendar")

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔓", help="Disconnect", use_container_width=True):
                st.session_state.google_token = None
                st.info("Disconnected from Google Calendar")
                st.rerun()

    st.divider()

    st.header("📊 Quick Stats")
    st.metric("Total Tasks", len(task_manager.get_all_tasks()))

    if task_manager.get_all_tasks():
        st.metric("Total Work Hours", f"{task_manager.total_hours:.1f}h")

        next_deadline = min(task.deadline for task in task_manager.get_all_tasks())
        st.metric("Next Deadline", next_deadline.strftime("%Y-%m-%d"))

    st.divider()

    if st.button("🔄 Reset All", use_container_width=True):
        task_manager.clear_all_tasks()
        st.session_state.schedule = None
        st.rerun()

    st.divider()
    st.markdown("### 📖 About")
    st.markdown("""
    This AI Task Planner uses Large Language Models to create
    optimized study schedules based on your tasks, deadlines,
    and personal preferences.

    **Architecture:** Clean, modular design with separate services
    for task management, scheduling, and calendar integration.
    """)
