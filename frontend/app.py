import streamlit as st
from datetime import datetime, timedelta
import json
import os
import sys
import time
from dotenv import load_dotenv

# --------- PATH SETUP: make sure project root is on sys.path ----------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------- BACKEND IMPORTS ----------
# Adjust these imports depending on how your backend package is structured.
# If you instead have them in backend.scheduler_service, change accordingly.
from backend import (
    get_credentials,
    fetch_calendar_events,
    build_chatgpt_payload,
    call_chatgpt_scheduler,
    push_events_to_google_calendar,
)

# ==================== SETUP ====================
st.set_page_config(page_title="AI Task Planner", page_icon="📅", layout="wide")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize session state
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "schedule" not in st.session_state:
    # will store whatever scheduled_events the backend returns (likely a list of dicts)
    st.session_state.schedule = None
if "preferences" not in st.session_state:
    st.session_state.preferences = {
        "study_windows": "",
        "max_daily_hours": 6,
        "break_pattern": "",
        "additional_notes": "",
    }

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
        subject = st.text_input("Subject (optional)", key="subject")
        deadline = st.date_input("Deadline *", min_value=datetime.today(), key="deadline")
        st.write("")  # spacer

    if st.button("➕ Add Task", type="primary"):
        if task_name and estimated_hours and deadline:
            new_task = {
                "id": len(st.session_state.tasks) + 1,
                "name": task_name,
                "subject": subject if subject else "General",
                "estimated_hours": estimated_hours,
                "deadline": deadline.strftime("%Y-%m-%d"),
                "priority": priority,
            }
            st.session_state.tasks.append(new_task)
            st.success(f"✅ Added: {task_name}")
            st.rerun()
        else:
            st.error("Please fill in all required fields (*)")

    st.divider()

    # Display tasks
    st.header(f"Your Tasks ({len(st.session_state.tasks)})")

    if len(st.session_state.tasks) == 0:
        st.info("📋 No tasks added yet. Add your first task above!")
    else:
        for idx, task in enumerate(st.session_state.tasks):
            col1, col2 = st.columns([5, 1])

            with col1:
                priority_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}
                st.markdown(
                    f"""
                    <div class="task-card">
                        <h4>{priority_emoji[task['priority']]} {task['name']}</h4>
                        <p>📚 {task['subject']} | ⏱️ {task['estimated_hours']}h | 📅 Due: {task['deadline']}</p>
                    </div>
                """,
                    unsafe_allow_html=True,
                )

            with col2:
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state.tasks.pop(idx)
                    st.rerun()

        st.divider()

        # Generate schedule button using BACKEND + LLM logic
        if st.button("🚀 Generate AI Schedule", type="primary", use_container_width=True):
            if not OPENAI_API_KEY:
                st.error("❌ OPENAI_API_KEY is not set. Please add it to your .env file.")
            else:
                with st.spinner("🤖 AI is creating your optimal schedule..."):
                    try:
                        # 1. Get Google credentials (your backend handles this)
                        creds = get_credentials()

                        # 2. Fetch existing calendar events
                        current_schedule = fetch_calendar_events(creds)

                        # 3. Build user info from preferences
                        user_info = {
                            "preferred_hours": st.session_state.preferences["study_windows"],
                            "max_daily_hours": st.session_state.preferences["max_daily_hours"],
                            "break_pattern": st.session_state.preferences["break_pattern"],
                            "notes": st.session_state.preferences["additional_notes"],
                        }

                        # 4. Build task list for backend / LLM
                        llm_tasks = []
                        for task in st.session_state.tasks:
                            llm_tasks.append(
                                {
                                    "title": task["name"],
                                    "estimated_duration_hours": task["estimated_hours"],
                                    "deadline": task["deadline"],
                                    "priority": task["priority"],
                                    "subject": task["subject"],
                                    "can_be_split": True,
                                }
                            )

                        # 5. Build payload and call LLM scheduler
                        payload = build_chatgpt_payload(user_info, current_schedule, llm_tasks)
                        scheduled_events = call_chatgpt_scheduler(payload, OPENAI_API_KEY)

                        # Save schedule in session
                        st.session_state.schedule = scheduled_events

                        if scheduled_events:
                            # 6. Push events to Google Calendar
                            push_events_to_google_calendar(creds, scheduled_events)
                            st.success("✅ Schedule generated and synced to Google Calendar!")
                            st.balloons()
                        else:
                            st.error("⚠️ AI returned no events. Please try again.")

                    except Exception as e:
                        st.error(f"❌ Error while generating schedule: {e}")

# ==================== TAB 2: PREFERENCES ====================
with tab2:
    st.header("⚙️ Study Preferences")
    st.markdown("*Configure your study habits and preferences*")

    study_windows = st.text_area(
        "Preferred Study Windows",
        value=st.session_state.preferences["study_windows"],
        placeholder="e.g., Weekday afternoons 2–6 PM, Weekend mornings 9–12",
        help="Describe when you prefer to study",
    )

    max_daily_hours = st.slider(
        "Maximum Daily Study Hours",
        min_value=1,
        max_value=12,
        value=st.session_state.preferences["max_daily_hours"],
        help="Maximum hours you want to study per day",
    )

    break_pattern = st.text_input(
        "Break Pattern",
        value=st.session_state.preferences["break_pattern"],
        placeholder="e.g., 15 min break every hour, 30 min lunch at 12 PM",
        help="Describe your preferred break schedule",
    )

    additional_notes = st.text_area(
        "Additional Notes",
        value=st.session_state.preferences["additional_notes"],
        placeholder="Any other preferences, constraints, or information...",
        help="Add any other relevant information for the AI",
    )

    if st.button("💾 Save Preferences", type="primary"):
        st.session_state.preferences = {
            "study_windows": study_windows,
            "max_daily_hours": max_daily_hours,
            "break_pattern": break_pattern,
            "additional_notes": additional_notes,
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
        # If your backend returns a list of events with keys 'title', 'start', 'end', 'description'
        # (as in your second snippet), we display them here.
        # Adjust keys if your backend uses slightly different names.
        st.subheader("📋 Scheduled Study Sessions")

        # Optional: simple summary
        try:
            total_events = len(schedule)
            unique_titles = len({e.get("title") for e in schedule})
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Events", total_events)
            with col2:
                st.metric("Distinct Tasks", unique_titles)
        except Exception:
            pass

        st.divider()

        for event in schedule:
            title = event.get("title", "Untitled")
            start = event.get("start", "")
            end = event.get("end", "")
            desc = event.get("description", "")

            st.markdown(
                f"""
                <div class="schedule-card">
                    <h4>{title}</h4>
                    <p>🕒 {start} → {end}</p>
                    <p>📝 {desc}</p>
                </div>
            """,
                unsafe_allow_html=True,
            )

        st.divider()

        # Download as JSON
        json_str = json.dumps(schedule, indent=2, default=str)
        st.download_button(
            label="📄 Download Schedule as JSON",
            data=json_str,
            file_name="schedule.json",
            mime="application/json",
            use_container_width=True,
        )

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("📊 Quick Stats")
    st.metric("Total Tasks", len(st.session_state.tasks))

    if st.session_state.tasks:
        total_hours = sum(task["estimated_hours"] for task in st.session_state.tasks)
        st.metric("Total Work Hours", f"{total_hours}h")

        next_deadline = min(task["deadline"] for task in st.session_state.tasks)
        st.metric("Next Deadline", next_deadline)

    st.divider()

    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.tasks = []
        st.session_state.schedule = None
        st.rerun()

    st.divider()
    st.markdown("### 📖 About")
    st.markdown(
        """
        This AI Task Planner uses Large Language Models to create 
        optimized study schedules based on your tasks, deadlines, 
        and personal preferences, and syncs them to your Google Calendar.
        """
    )
