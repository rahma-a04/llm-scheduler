import streamlit as st
from datetime import datetime, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="AI Task Planner",
    page_icon="📅",
    layout="wide"
)

# Initialize session state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'schedule' not in st.session_state:
    st.session_state.schedule = None
if 'preferences' not in st.session_state:
    st.session_state.preferences = {
        'study_windows': '',
        'max_daily_hours': 6,
        'break_pattern': '',
        'additional_notes': ''
    }

# Custom CSS for better styling
st.markdown("""
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
        border-left: 4px solid #4f46e5;
        background-color: white;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("📅 AI Task Planner")
st.markdown("*Smart scheduling powered by LLM*")
st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Tasks", "⚙️ Preferences", "📆 Schedule"])

# ==================== TAB 1: TASKS ====================
with tab1:
    st.header("Add New Task")
    
    # Task input form
    col1, col2 = st.columns(2)
    
    with col1:
        task_name = st.text_input("Task Name *", key="task_name")
        estimated_hours = st.number_input("Estimated Hours *", min_value=0.5, max_value=20.0, step=0.5, key="est_hours")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1, key="priority")
    
    with col2:
        subject = st.text_input("Subject (optional)", key="subject")
        deadline = st.date_input("Deadline *", min_value=datetime.today(), key="deadline")
        st.write("")  # Spacer
    
    if st.button("➕ Add Task", type="primary"):
        if task_name and estimated_hours and deadline:
            new_task = {
                'id': len(st.session_state.tasks) + 1,
                'name': task_name,
                'subject': subject if subject else "General",
                'estimated_hours': estimated_hours,
                'deadline': deadline.strftime("%Y-%m-%d"),
                'priority': priority
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
                st.markdown(f"""
                    <div class="task-card">
                        <h4>{priority_emoji[task['priority']]} {task['name']}</h4>
                        <p>📚 {task['subject']} | ⏱️ {task['estimated_hours']}h | 📅 Due: {task['deadline']}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state.tasks.pop(idx)
                    st.rerun()
        
        st.divider()
        
        # Generate schedule button
        if st.button("🚀 Generate AI Schedule", type="primary", use_container_width=True):
            with st.spinner("🤖 AI is creating your optimal schedule..."):
                # Call your backend function here
                schedule = generate_schedule_with_llm(
                    st.session_state.tasks, 
                    st.session_state.preferences
                )
                st.session_state.schedule = schedule
                st.success("✅ Schedule generated successfully!")
                st.balloons()

# ==================== TAB 2: PREFERENCES ====================
with tab2:
    st.header("⚙️ Study Preferences")
    st.markdown("*Configure your study habits and preferences*")
    
    study_windows = st.text_area(
        "Preferred Study Windows",
        value=st.session_state.preferences['study_windows'],
        placeholder="e.g., Weekday afternoons 2-6 PM, Weekend mornings 9 AM-12 PM",
        help="Describe when you prefer to study"
    )
    
    max_daily_hours = st.slider(
        "Maximum Daily Study Hours",
        min_value=1,
        max_value=12,
        value=st.session_state.preferences['max_daily_hours'],
        help="Maximum hours you want to study per day"
    )
    
    break_pattern = st.text_input(
        "Break Pattern",
        value=st.session_state.preferences['break_pattern'],
        placeholder="e.g., 15 min break every hour, 30 min lunch at 12 PM",
        help="Describe your preferred break schedule"
    )
    
    additional_notes = st.text_area(
        "Additional Notes",
        value=st.session_state.preferences['additional_notes'],
        placeholder="Any other preferences, constraints, or information...",
        help="Add any other relevant information for the AI"
    )
    
    if st.button("💾 Save Preferences", type="primary"):
        st.session_state.preferences = {
            'study_windows': study_windows,
            'max_daily_hours': max_daily_hours,
            'break_pattern': break_pattern,
            'additional_notes': additional_notes
        }
        st.success("✅ Preferences saved!")
    
    st.info("💡 **Tip:** These preferences help the AI create a personalized schedule that fits your study style and availability.")

# ==================== TAB 3: SCHEDULE ====================
with tab3:
    st.header("📆 Your AI-Generated Schedule")
    
    if st.session_state.schedule is None:
        st.info("📋 No schedule generated yet. Add tasks and click 'Generate AI Schedule' to get started!")
    else:
        schedule = st.session_state.schedule
        
        # Summary cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tasks", schedule['summary']['total_tasks'])
        with col2:
            st.metric("Total Hours", f"{schedule['summary']['total_hours']}h")
        with col3:
            st.metric("Days Scheduled", schedule['summary']['days_used'])
        
        st.divider()
        
        # Scheduled sessions
        st.subheader("📋 Scheduled Study Sessions")
        
        for event in schedule['events']:
            st.markdown(f"""
                <div class="schedule-card">
                    <h4>{event['task_name']}</h4>
                    <p>📅 {event['date']} | ⏰ {event['start_time']} | ⏱️ {event['duration']}h | 📚 {event['type']}</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export to Google Calendar", type="primary", use_container_width=True):
                export_to_google_calendar(schedule)
                st.success("✅ Exported to Google Calendar!")
        
        with col2:
            if st.button("📄 Download as JSON", use_container_width=True):
                json_str = json.dumps(schedule, indent=2)
                st.download_button(
                    label="💾 Download JSON",
                    data=json_str,
                    file_name="schedule.json",
                    mime="application/json"
                )

# Sidebar
with st.sidebar:
    st.header("📊 Quick Stats")
    st.metric("Total Tasks", len(st.session_state.tasks))
    
    if st.session_state.tasks:
        total_hours = sum(task['estimated_hours'] for task in st.session_state.tasks)
        st.metric("Total Work Hours", f"{total_hours}h")
        
        # Upcoming deadline
        if st.session_state.tasks:
            next_deadline = min(task['deadline'] for task in st.session_state.tasks)
            st.metric("Next Deadline", next_deadline)
    
    st.divider()
    
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.tasks = []
        st.session_state.schedule = None
        st.rerun()
    
    st.divider()
    st.markdown("### 📖 About")
    st.markdown("""
    This AI Task Planner uses Large Language Models to create 
    optimized study schedules based on your tasks, deadlines, 
    and personal preferences.
    """)


# ==================== BACKEND FUNCTIONS ====================
# Replace these with your actual backend logic

def generate_schedule_with_llm(tasks, preferences):
    """
    This is where you'll integrate your LLM API call and scheduling logic.
    
    Args:
        tasks: List of task dictionaries
        preferences: Dictionary of user preferences
    
    Returns:
        Dictionary containing the generated schedule
    """
    # TODO: Replace with your actual LLM API call
    # Example structure:
    # 1. Build prompt from tasks and preferences
    # 2. Call OpenAI API
    # 3. Parse LLM response
    # 4. Validate schedule
    # 5. Return structured schedule
    
    # Mock implementation for demonstration
    import time
    time.sleep(2)  # Simulate API call
    
    events = []
    for task in tasks:
        sessions = int(task['estimated_hours'] / 2) + 1
        deadline_date = datetime.strptime(task['deadline'], "%Y-%m-%d")
        
        for i in range(sessions):
            session_date = deadline_date - timedelta(days=(sessions - i))
            events.append({
                'task_name': task['name'],
                'date': session_date.strftime("%Y-%m-%d"),
                'start_time': '14:00',
                'duration': min(2, task['estimated_hours'] - i * 2),
                'type': task['subject']
            })
    
    return {
        'events': events,
        'summary': {
            'total_tasks': len(tasks),
            'total_hours': sum(t['estimated_hours'] for t in tasks),
            'days_used': len(set(e['date'] for e in events))
        }
    }


def export_to_google_calendar(schedule):
    """
    This is where you'll integrate Google Calendar API.
    
    Args:
        schedule: Dictionary containing the schedule to export
    """
    # TODO: Implement Google Calendar API integration
    # 1. Authenticate with Google Calendar API
    # 2. Create events for each scheduled session
    # 3. Handle conflicts and errors
    pass