# AI Task Planner

An intelligent task scheduling application that uses Large Language Models (LLMs) to create optimized study schedules based on your tasks, deadlines, and personal preferences. Built with Streamlit and powered by OpenAI's GPT-4.

## Features

- **Smart AI Scheduling**: Automatically generates optimal study schedules using LLM reasoning
- **Google Calendar Integration**: Sync your existing calendar events and export generated schedules
- **Flexible Task Management**: Add tasks with priorities, deadlines, and estimated hours
- **Personalized Preferences**: Configure study hours, daily limits, and buffer times
- **Conflict Detection**: Automatically avoids scheduling conflicts and respects your availability
- **Baseline Comparison**: Switch between AI-powered and greedy baseline scheduling algorithms

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- OpenAI API key
- (Optional) Google Cloud credentials for calendar integration

### Quick Start

1. **Clone the repository**
   ```bash
   cd llm-scheduler
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   Or use the install script:
   ```bash
   cd scripts
   python install.py
   ```

3. **Set up environment variables**

   Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=your-openai-api-key-here
   DEFAULT_SCHEDULER=llm
   LLM_MODEL=gpt-4o
   DEFAULT_MAX_DAILY_HOURS=6
   DEFAULT_BUFFER_MINUTES=15
   ```

4. **(Optional) Set up Google Calendar integration**

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download credentials and save as `credentials.json` in the project root
   - Update your `.env` file:
     ```bash
     GOOGLE_CREDENTIALS_PATH=./credentials.json
     ```

## Running the App

From the project root:

```bash
streamlit run ui/app.py
```

Or from the `ui` directory:

```bash
cd ui
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## Usage Guide

### 1. Add Tasks

In the "Tasks" tab:
- Enter task name, subject, estimated hours, priority, and deadline
- Click "Add Task" to add it to your task list
- Repeat for all tasks you want to schedule

### 2. Configure Preferences

In the "Preferences" tab:
- Set your preferred study hours (e.g., 9:00 AM to 10:00 PM)
- Set maximum daily study hours
- Configure buffer time between events
- Click "Save Preferences"

### 3. (Optional) Connect Google Calendar

In the sidebar:
- Click "Connect Google Calendar"
- Authorize the application
- Your existing calendar events will be considered when generating schedules

### 4. Generate Schedule

In the "Tasks" tab:
- Click "Generate AI Schedule" (or "Generate Schedule" for baseline)
- The AI will analyze your tasks, existing events, and preferences
- Wait a few seconds for the optimized schedule to be generated

### 5. View and Export

In the "Schedule" tab:
- Review the generated schedule with all study sessions
- Export to Google Calendar (if connected)
- Download as JSON for backup or sharing

## Configuration Options

You can customize the app behavior via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) | None |
| `DEFAULT_SCHEDULER` | Scheduler type: `llm` or `baseline` | `llm` |
| `LLM_MODEL` | OpenAI model to use | `gpt-4o` |
| `DEFAULT_MAX_DAILY_HOURS` | Maximum study hours per day | `6` |
| `DEFAULT_BUFFER_MINUTES` | Buffer time between events | `15` |
| `GOOGLE_CREDENTIALS_PATH` | Path to Google credentials | `../credentials.json` |

## Scheduler Modes

### LLM Scheduler (Default)
Uses GPT-4 to intelligently distribute tasks across available time slots, considering:
- Task priorities and deadlines
- Existing calendar commitments
- User preferences and study habits
- Optimal task distribution strategies
- Burnout prevention

**Requires**: OpenAI API key (costs ~$0.01-0.05 per schedule)

### Baseline Scheduler
A deterministic greedy algorithm that:
- Schedules tasks as early as possible
- Respects deadlines and priorities
- Fills available time slots sequentially

**Requires**: No API key (free)

Switch between modes by setting `DEFAULT_SCHEDULER` in your `.env` file.

## Project Structure

```
llm-scheduler/
├── backend/              # Core scheduling logic
│   ├── models.py         # Data models (Task, Schedule, etc.)
│   ├── scheduler_service.py  # LLM and baseline schedulers
│   ├── calendar_service.py   # Google Calendar integration
│   ├── task_manager.py       # Task management
│   └── config.py         # Configuration and settings
├── ui/                   # Streamlit web interface
│   └── app.py            # Main application
├── scripts/              # Utility scripts
│   ├── install.py        # Dependency installer
│   ├── uninstall.py      # Dependency remover
│   └── cleanup.py        # Cleanup script
├── evaluation/           # Evaluation pipeline (see below)
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
└── README.md             # This file
```

## For Researchers & Evaluators

If you're looking to evaluate different prompting strategies or run the full evaluation pipeline, see:

- **[evaluation/README.md](evaluation/README.md)** - Comprehensive evaluation framework documentation
- **[evaluation/instructions.md](evaluation/instructions.md)** - Detailed setup and usage instructions

The evaluation pipeline includes:
- 30 carefully designed test cases
- 4 prompting strategies (zero-shot, few-shot, chain-of-thought, constraint-first)
- Comprehensive metrics (conflicts, deadlines, workload balance, cost)
- Automated testing and visualization

To install evaluation dependencies:
```bash
pip install -r requirements.txt
pip install -r evaluation/requirements-eval.txt
```

## Troubleshooting

### "OPENAI_API_KEY is not set"
- Make sure you've created a `.env` file in the project root
- Verify your API key is correctly set in the `.env` file
- Restart the Streamlit app after changing environment variables

### Google Calendar connection fails
- Verify `credentials.json` exists and is valid
- Delete any existing `token.json` files and try reconnecting
- Ensure Google Calendar API is enabled in your Google Cloud project
- Check that the OAuth consent screen is properly configured

### Schedule generation returns no events
- Check that your tasks have realistic deadlines (in the future)
- Verify that there's enough time between now and the deadline
- Try reducing the estimated hours or extending the deadline
- Check the console for error messages

### Import errors
```bash
pip install --upgrade -r requirements.txt
```

## Maintenance Scripts

From the `scripts/` directory:

```bash
# Install all dependencies
python install.py

# Uninstall all dependencies
python uninstall.py

# Clean up generated files
python cleanup.py
```

## Cost Estimation

Using the LLM scheduler with GPT-4:
- **Per schedule generation**: ~$0.01 - $0.05
- **Typical usage (5-10 schedules/day)**: ~$0.05 - $0.50/day
- **Monthly (light usage)**: ~$1.50 - $15/month

The baseline scheduler is completely free (no API calls).

## Requirements

**Core Dependencies:**
- streamlit - Web application framework
- openai - OpenAI API client
- google-api-python-client - Google Calendar API
- google-auth - Google authentication
- streamlit-oauth - OAuth integration
- python-dotenv - Environment variable management

See `requirements.txt` for complete list with version specifications.

## Contributing

This is a CS 4701 final project. For questions or issues, please contact the project maintainers.

## License

This project is for educational purposes as part of Cornell CS 4701.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [OpenAI GPT-4](https://openai.com/)
- Google Calendar integration via [Google Calendar API](https://developers.google.com/calendar)

---

**Last updated**: December 13, 2025
