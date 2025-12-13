"""
Evaluation metrics for scheduler comparison.

This module provides functions to compute various metrics for evaluating
scheduling quality, constraint satisfaction, and system performance.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from collections import defaultdict
import json
import re


class ScheduleMetrics:
    """Container for all metrics computed for a schedule."""

    def __init__(self):
        # Constraint/correctness metrics
        self.conflict_free: bool = True
        self.num_conflicts: int = 0
        self.deadline_compliance_rate: float = 0.0
        self.tasks_meeting_deadline: int = 0
        self.total_tasks: int = 0

        # Quality/utility metrics
        self.workload_variance: float = 0.0
        self.average_daily_hours: float = 0.0
        self.completion_ratio: float = 0.0
        self.hours_scheduled: float = 0.0
        self.hours_requested: float = 0.0
        self.fragmentation_score: float = 0.0
        self.makespan_days: float = 0.0

        # Parsing metrics
        self.parsing_success: bool = True
        self.repair_attempted: bool = False
        self.parse_error_message: str = ""

        # System metrics
        self.api_cost: float = 0.0
        self.latency_seconds: float = 0.0
        self.total_tokens: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0

        # Preference compliance
        self.within_working_hours_rate: float = 0.0
        self.weekend_violation: bool = False

        # LLM-based quality metrics
        self.llm_quality_score: float = 0.0
        self.llm_quality_reasoning: str = ""
        self.llm_preference_score: float = 0.0
        self.llm_preference_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            # Constraint metrics
            'conflict_free': self.conflict_free,
            'num_conflicts': self.num_conflicts,
            'deadline_compliance_rate': self.deadline_compliance_rate,
            'tasks_meeting_deadline': self.tasks_meeting_deadline,
            'total_tasks': self.total_tasks,

            # Quality metrics
            'workload_variance': self.workload_variance,
            'average_daily_hours': self.average_daily_hours,
            'completion_ratio': self.completion_ratio,
            'hours_scheduled': self.hours_scheduled,
            'hours_requested': self.hours_requested,
            'fragmentation_score': self.fragmentation_score,
            'makespan_days': self.makespan_days,

            # Parsing metrics
            'parsing_success': self.parsing_success,
            'repair_attempted': self.repair_attempted,
            'parse_error_message': self.parse_error_message,

            # System metrics
            'api_cost': self.api_cost,
            'latency_seconds': self.latency_seconds,
            'total_tokens': self.total_tokens,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,

            # Preference compliance
            'within_working_hours_rate': self.within_working_hours_rate,
            'weekend_violation': self.weekend_violation,

            # LLM-based quality metrics
            'llm_quality_score': self.llm_quality_score,
            'llm_quality_reasoning': self.llm_quality_reasoning,
            'llm_preference_score': self.llm_preference_score,
            'llm_preference_reasoning': self.llm_preference_reasoning,
        }


def check_conflicts(scheduled_events: List[Dict[str, Any]],
                   existing_events: List[Dict[str, Any]]) -> tuple[bool, int]:
    """Check if there are any overlapping events.

    Args:
        scheduled_events: List of newly scheduled events
        existing_events: List of existing calendar events

    Returns:
        Tuple of (conflict_free: bool, num_conflicts: int)
    """
    all_events = scheduled_events + existing_events
    conflicts = 0

    for i, event1 in enumerate(all_events):
        start1 = _parse_datetime(event1.get('start', ''))
        end1 = _parse_datetime(event1.get('end', ''))

        if not start1 or not end1:
            continue

        for event2 in all_events[i+1:]:
            start2 = _parse_datetime(event2.get('start', ''))
            end2 = _parse_datetime(event2.get('end', ''))

            if not start2 or not end2:
                continue

            # Check for overlap: (start1 < end2) and (start2 < end1)
            if start1 < end2 and start2 < end1:
                conflicts += 1

    return conflicts == 0, conflicts


def check_deadline_compliance(scheduled_events: List[Dict[str, Any]],
                              tasks: List[Dict[str, Any]]) -> tuple[float, int, int]:
    """Check what fraction of tasks meet their deadlines.

    Args:
        scheduled_events: List of scheduled events
        tasks: List of task specifications with deadlines

    Returns:
        Tuple of (compliance_rate, tasks_meeting_deadline, total_tasks)
    """
    if not tasks:
        return 1.0, 0, 0

    # Group scheduled events by task
    task_schedules = defaultdict(list)
    for event in scheduled_events:
        # Try to extract task ID from title or description
        task_name = event.get('title', '')
        # Match task by name similarity
        for task in tasks:
            if task['name'].lower() in task_name.lower():
                task_schedules[task['id']].append(event)
                break

    tasks_meeting_deadline = 0

    for task in tasks:
        task_id = task['id']
        deadline = _parse_datetime(task['deadline'])

        if not deadline:
            continue

        # Check if all events for this task finish before deadline
        task_events = task_schedules.get(task_id, [])

        if not task_events:
            # Task not scheduled at all
            continue

        # Find the latest end time for this task
        latest_end = None
        for event in task_events:
            end_time = _parse_datetime(event.get('end', ''))
            if end_time:
                if latest_end is None or end_time > latest_end:
                    latest_end = end_time

        if latest_end and latest_end <= deadline:
            tasks_meeting_deadline += 1

    compliance_rate = tasks_meeting_deadline / len(tasks) if tasks else 0.0
    return compliance_rate, tasks_meeting_deadline, len(tasks)


def compute_workload_balance(scheduled_events: List[Dict[str, Any]]) -> tuple[float, float]:
    """Compute workload variance and average daily hours.

    Lower variance indicates better balance across days.

    Args:
        scheduled_events: List of scheduled events

    Returns:
        Tuple of (variance, average_daily_hours)
    """
    if not scheduled_events:
        return 0.0, 0.0

    # Group events by day
    daily_hours = defaultdict(float)

    for event in scheduled_events:
        start = _parse_datetime(event.get('start', ''))
        end = _parse_datetime(event.get('end', ''))

        if not start or not end:
            continue

        day = start.date()
        duration_hours = (end - start).total_seconds() / 3600
        daily_hours[day] += duration_hours

    if not daily_hours:
        return 0.0, 0.0

    hours_list = list(daily_hours.values())
    variance = float(np.var(hours_list))
    average = float(np.mean(hours_list))

    return variance, average


def compute_completion_ratio(scheduled_events: List[Dict[str, Any]],
                            tasks: List[Dict[str, Any]]) -> tuple[float, float, float]:
    """Compute what fraction of requested hours were scheduled.

    Args:
        scheduled_events: List of scheduled events
        tasks: List of tasks with estimated hours

    Returns:
        Tuple of (completion_ratio, hours_scheduled, hours_requested)
    """
    hours_requested = sum(task.get('estimated_hours', 0.0) for task in tasks)

    hours_scheduled = 0.0
    for event in scheduled_events:
        start = _parse_datetime(event.get('start', ''))
        end = _parse_datetime(event.get('end', ''))

        if start and end:
            hours_scheduled += (end - start).total_seconds() / 3600

    completion_ratio = hours_scheduled / hours_requested if hours_requested > 0 else 0.0

    return completion_ratio, hours_scheduled, hours_requested


def compute_fragmentation(scheduled_events: List[Dict[str, Any]],
                         tasks: List[Dict[str, Any]]) -> float:
    """Compute fragmentation score (average blocks per task).

    Lower is better - indicates less task splitting.

    Args:
        scheduled_events: List of scheduled events
        tasks: List of tasks

    Returns:
        Average number of blocks per task
    """
    if not tasks or not scheduled_events:
        return 0.0

    # Count blocks per task
    task_blocks = defaultdict(int)

    for event in scheduled_events:
        task_name = event.get('title', '')
        # Match to tasks
        for task in tasks:
            if task['name'].lower() in task_name.lower():
                task_blocks[task['id']] += 1
                break

    if not task_blocks:
        return 0.0

    return sum(task_blocks.values()) / len(task_blocks)


def compute_makespan(scheduled_events: List[Dict[str, Any]]) -> float:
    """Compute makespan in days (span between earliest and latest events).

    Args:
        scheduled_events: List of scheduled events

    Returns:
        Makespan in days
    """
    if not scheduled_events:
        return 0.0

    earliest = None
    latest = None

    for event in scheduled_events:
        start = _parse_datetime(event.get('start', ''))
        end = _parse_datetime(event.get('end', ''))

        if start:
            if earliest is None or start < earliest:
                earliest = start

        if end:
            if latest is None or end > latest:
                latest = end

    if earliest and latest:
        return (latest - earliest).total_seconds() / 86400  # Convert to days

    return 0.0


def check_working_hours_compliance(scheduled_events: List[Dict[str, Any]],
                                   preferences: Dict[str, Any]) -> tuple[float, bool]:
    """Check compliance with working hours and weekend preferences.

    Args:
        scheduled_events: List of scheduled events
        preferences: User preferences including study_windows and additional_notes

    Returns:
        Tuple of (within_working_hours_rate, weekend_violation)
    """
    if not scheduled_events:
        return 1.0, False

    # study_windows = preferences.get('study_windows', '')  # Reserved for future use
    additional_notes = preferences.get('additional_notes', '').lower()
    no_weekends = 'no weekend' in additional_notes or "don't work on weekend" in additional_notes

    events_in_hours = 0
    weekend_violation = False

    for event in scheduled_events:
        start = _parse_datetime(event.get('start', ''))

        if not start:
            continue

        # Check weekend violation
        if no_weekends and start.weekday() >= 5:  # Saturday=5, Sunday=6
            weekend_violation = True

        # Check working hours (simplified - just count as compliant if exists)
        # In a real implementation, would parse study_windows and check
        events_in_hours += 1

    within_hours_rate = events_in_hours / len(scheduled_events) if scheduled_events else 1.0

    return within_hours_rate, weekend_violation


def evaluate_schedule_quality_with_llm(
    scheduled_events: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    existing_events: List[Dict[str, Any]],
    openai_client: Optional[Any] = None,
    model: str = "gpt-4o-mini"
) -> tuple[float, str]:
    """Use LLM to evaluate overall schedule quality.

    Args:
        scheduled_events: List of newly scheduled events
        tasks: List of task specifications
        existing_events: List of existing calendar events
        openai_client: OpenAI client instance (optional)
        model: Model to use for evaluation (default: gpt-4o-mini for cost efficiency)

    Returns:
        Tuple of (quality_score, reasoning)
        quality_score: 0-100 score indicating schedule quality
        reasoning: Text explanation of the score
    """
    if openai_client is None:
        return 0.0, "No OpenAI client provided"

    if not scheduled_events:
        return 0.0, "No events scheduled"

    # Build evaluation prompt
    system_prompt = """You are an expert schedule quality evaluator for student study schedules.

Your task is to evaluate the quality of a generated study schedule based on multiple factors:

1. **Task Distribution**: Are tasks spread reasonably across days, or crammed into a few days?
2. **Workload Balance**: Is the daily workload balanced, or are some days overloaded?
3. **Time Block Appropriateness**: Are study sessions reasonable lengths (30min-3hrs)?
4. **Task Fragmentation**: Are tasks split appropriately, or over-fragmented into too many small blocks?
5. **Deadline Awareness**: Are urgent tasks prioritized and scheduled closer to today?
6. **Conflict Avoidance**: Do scheduled events avoid overlapping with existing commitments?
7. **Overall Feasibility**: Does the schedule seem realistic and executable for a student?

Provide a score from 0-100 where:
- 90-100: Excellent schedule, well-balanced and thoughtful
- 70-89: Good schedule with minor issues
- 50-69: Acceptable schedule with some problems
- 30-49: Poor schedule with significant issues
- 0-29: Very poor or infeasible schedule

Return your response as JSON:
{
  "score": <number between 0-100>,
  "reasoning": "<brief explanation of score, 2-3 sentences>"
}"""

    user_prompt = f"""Evaluate this study schedule:

**Tasks to Schedule:**
{json.dumps(tasks, indent=2)}

**Existing Calendar Events:**
{json.dumps(existing_events, indent=2)}

**Generated Schedule:**
{json.dumps(scheduled_events, indent=2)}

Please evaluate the quality of this schedule and return your assessment as JSON."""

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        result_text = response.choices[0].message.content.strip()

        # Remove markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?|```$", "", result_text.strip(), flags=re.MULTILINE).strip()

        # Parse JSON
        result = json.loads(cleaned)
        score = float(result.get("score", 0))
        reasoning = result.get("reasoning", "No reasoning provided")

        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))

        return score, reasoning

    except Exception as e:
        return 0.0, f"Error evaluating schedule: {str(e)}"


def evaluate_preference_adherence_with_llm(
    scheduled_events: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    preferences: Dict[str, Any],
    openai_client: Optional[Any] = None,
    model: str = "gpt-4o-mini"
) -> tuple[float, str]:
    """Use LLM to evaluate how well the schedule adheres to user preferences.

    Args:
        scheduled_events: List of newly scheduled events
        tasks: List of task specifications
        preferences: User preferences dictionary
        openai_client: OpenAI client instance (optional)
        model: Model to use for evaluation (default: gpt-4o-mini for cost efficiency)

    Returns:
        Tuple of (adherence_score, reasoning)
        adherence_score: 0-100 score indicating preference adherence
        reasoning: Text explanation of the score
    """
    if openai_client is None:
        return 0.0, "No OpenAI client provided"

    if not scheduled_events:
        return 0.0, "No events scheduled"

    # Build evaluation prompt
    system_prompt = """You are an expert evaluator of schedule adherence to user preferences.

Your task is to evaluate how well a generated study schedule follows the user's stated preferences.

Evaluate based on:
1. **Study Windows**: Are events scheduled within preferred study windows?
2. **Daily Hour Limits**: Does the schedule respect max daily hours?
3. **Break Patterns**: Are breaks incorporated as requested?
4. **Additional Notes**: Are special requests honored (e.g., "no weekends", "morning preference", etc.)?

Provide a score from 0-100 where:
- 90-100: Excellent adherence, all preferences followed
- 70-89: Good adherence with minor deviations
- 50-69: Acceptable adherence with some violations
- 30-49: Poor adherence with significant violations
- 0-29: Very poor adherence, preferences largely ignored

Return your response as JSON:
{
  "score": <number between 0-100>,
  "reasoning": "<brief explanation of score, 2-3 sentences>"
}"""

    user_prompt = f"""Evaluate how well this schedule adheres to user preferences:

**User Preferences:**
{json.dumps(preferences, indent=2)}

**Tasks to Schedule:**
{json.dumps(tasks, indent=2)}

**Generated Schedule:**
{json.dumps(scheduled_events, indent=2)}

Please evaluate the adherence to preferences and return your assessment as JSON."""

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        result_text = response.choices[0].message.content.strip()

        # Remove markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?|```$", "", result_text.strip(), flags=re.MULTILINE).strip()

        # Parse JSON
        result = json.loads(cleaned)
        score = float(result.get("score", 0))
        reasoning = result.get("reasoning", "No reasoning provided")

        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))

        return score, reasoning

    except Exception as e:
        return 0.0, f"Error evaluating preferences: {str(e)}"


def calculate_api_cost(prompt_tokens: int, completion_tokens: int,
                      model: str = "gpt-4o") -> float:
    """Calculate API cost based on token usage.

    Args:
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        model: Model name

    Returns:
        Cost in USD
    """
    # Pricing as of 2024 (update as needed)
    # GPT-4o pricing
    if model == "gpt-4o":
        prompt_cost_per_1k = 0.005  # $5 per 1M tokens = $0.005 per 1K
        completion_cost_per_1k = 0.015  # $15 per 1M tokens = $0.015 per 1K
    elif model == "gpt-4":
        prompt_cost_per_1k = 0.03
        completion_cost_per_1k = 0.06
    elif model == "gpt-3.5-turbo":
        prompt_cost_per_1k = 0.0015
        completion_cost_per_1k = 0.002
    else:
        # Default to GPT-4o pricing
        prompt_cost_per_1k = 0.005
        completion_cost_per_1k = 0.015

    total_cost = (
        (prompt_tokens / 1000) * prompt_cost_per_1k +
        (completion_tokens / 1000) * completion_cost_per_1k
    )

    return total_cost


def compute_all_metrics(
    scheduled_events: List[Dict[str, Any]],
    existing_events: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    preferences: Dict[str, Any],
    parsing_success: bool = True,
    repair_attempted: bool = False,
    parse_error: str = "",
    latency_seconds: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    model: str = "gpt-4o",
    openai_client: Optional[Any] = None,
    evaluate_with_llm: bool = False
) -> ScheduleMetrics:
    """Compute all metrics for a schedule.

    Args:
        scheduled_events: Newly scheduled events
        existing_events: Existing calendar events
        tasks: Task specifications
        preferences: User preferences
        parsing_success: Whether JSON parsing succeeded
        repair_attempted: Whether repair was attempted
        parse_error: Error message if parsing failed
        latency_seconds: API latency
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        model: Model name for cost calculation
        openai_client: OpenAI client for LLM-based evaluation (optional)
        evaluate_with_llm: Whether to run LLM-based quality evaluation

    Returns:
        ScheduleMetrics object with all computed metrics
    """
    metrics = ScheduleMetrics()

    # Parsing metrics
    metrics.parsing_success = parsing_success
    metrics.repair_attempted = repair_attempted
    metrics.parse_error_message = parse_error

    # System metrics
    metrics.latency_seconds = latency_seconds
    metrics.prompt_tokens = prompt_tokens
    metrics.completion_tokens = completion_tokens
    metrics.total_tokens = prompt_tokens + completion_tokens
    metrics.api_cost = calculate_api_cost(prompt_tokens, completion_tokens, model)

    # Only compute quality metrics if parsing succeeded
    if parsing_success and scheduled_events:
        # Conflict metrics
        conflict_free, num_conflicts = check_conflicts(scheduled_events, existing_events)
        metrics.conflict_free = conflict_free
        metrics.num_conflicts = num_conflicts

        # Deadline compliance
        compliance, meeting, total = check_deadline_compliance(scheduled_events, tasks)
        metrics.deadline_compliance_rate = compliance
        metrics.tasks_meeting_deadline = meeting
        metrics.total_tasks = total

        # Workload balance
        variance, avg_hours = compute_workload_balance(scheduled_events)
        metrics.workload_variance = variance
        metrics.average_daily_hours = avg_hours

        # Completion ratio
        ratio, scheduled, requested = compute_completion_ratio(scheduled_events, tasks)
        metrics.completion_ratio = ratio
        metrics.hours_scheduled = scheduled
        metrics.hours_requested = requested

        # Fragmentation
        metrics.fragmentation_score = compute_fragmentation(scheduled_events, tasks)

        # Makespan
        metrics.makespan_days = compute_makespan(scheduled_events)

        # Working hours compliance
        within_rate, weekend_viol = check_working_hours_compliance(
            scheduled_events, preferences
        )
        metrics.within_working_hours_rate = within_rate
        metrics.weekend_violation = weekend_viol

        # LLM-based evaluation (optional)
        if evaluate_with_llm and openai_client:
            # Evaluate schedule quality
            quality_score, quality_reasoning = evaluate_schedule_quality_with_llm(
                scheduled_events, tasks, existing_events, openai_client
            )
            metrics.llm_quality_score = quality_score
            metrics.llm_quality_reasoning = quality_reasoning

            # Evaluate preference adherence
            pref_score, pref_reasoning = evaluate_preference_adherence_with_llm(
                scheduled_events, tasks, preferences, openai_client
            )
            metrics.llm_preference_score = pref_score
            metrics.llm_preference_reasoning = pref_reasoning
    else:
        # Set total_tasks for reporting even if parsing failed
        metrics.total_tasks = len(tasks)

    return metrics


def _parse_datetime(dt_string: Any) -> datetime | None:
    """Parse datetime from various formats.

    Args:
        dt_string: Datetime string or dict

    Returns:
        Datetime object or None if parsing fails (always timezone-naive)
    """
    if isinstance(dt_string, datetime):
        # Normalize to naive datetime
        if dt_string.tzinfo is not None:
            return dt_string.replace(tzinfo=None)
        return dt_string

    if isinstance(dt_string, dict):
        dt_string = dt_string.get('dateTime', dt_string.get('date', ''))

    if not isinstance(dt_string, str):
        return None

    if not dt_string:
        return None

    try:
        # Try ISO format with timezone
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        # Normalize to naive datetime for consistent comparisons
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, AttributeError):
        pass

    try:
        # Try date only (add time component)
        if 'T' not in dt_string:
            dt_string = f"{dt_string}T23:59:59"
        dt = datetime.fromisoformat(dt_string)
        # Normalize to naive datetime
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, AttributeError):
        pass

    return None
