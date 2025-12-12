"""
Evaluation pipeline for comparing scheduling algorithms.

This module provides the main evaluation framework for testing baseline
and LLM-based schedulers across multiple test cases and prompting strategies.
"""

import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, time as time_type
from openai import OpenAI

from backend.models import Task, CalendarEvent, UserPreferences, WorkingHours, Priority, Schedule
from backend.scheduler_service import BaselineScheduler, LLMScheduler
from evaluation.prompts import get_strategy, list_strategies
from evaluation.metrics import compute_all_metrics, ScheduleMetrics


class Evaluator:
    """Main evaluation pipeline for scheduler comparison."""

    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        """Initialize evaluator.

        Args:
            openai_api_key: OpenAI API key
            model: Model to use for LLM scheduler
        """
        self.openai_api_key = openai_api_key
        self.model = model
        self.client = OpenAI(api_key=openai_api_key)
        self.baseline_scheduler = BaselineScheduler()

    def load_test_cases(self, test_file: str = "evaluation/tests.json") -> List[Dict[str, Any]]:
        """Load test cases from JSON file.

        Args:
            test_file: Path to test cases JSON file

        Returns:
            List of test case dictionaries
        """
        with open(test_file, 'r') as f:
            test_cases = json.load(f)
        return test_cases

    def parse_test_case(self, test_case: Dict[str, Any]) -> tuple:
        """Parse test case into model objects.

        Args:
            test_case: Test case dictionary

        Returns:
            Tuple of (tasks, existing_events, preferences)
        """
        # Parse tasks
        tasks = []
        for task_data in test_case.get('new_tasks', []):
            deadline_str = task_data['deadline']
            # Parse deadline (may be date or datetime)
            if 'T' in deadline_str:
                deadline = datetime.fromisoformat(deadline_str)
            else:
                # Convert date to datetime (end of day)
                deadline = datetime.fromisoformat(f"{deadline_str}T23:59:59")

            task = Task(
                id=str(task_data['id']),
                name=task_data['name'],
                subject=task_data['subject'],
                estimated_hours=float(task_data['estimated_hours']),
                deadline=deadline,
                priority=Priority(task_data.get('priority', 'medium')),
                can_be_split=task_data.get('can_be_split', True)
            )
            tasks.append(task)

        # Parse existing events
        existing_events = []
        for event_data in test_case.get('existing_events', []):
            start_dt = event_data['start'].get('dateTime', event_data['start'].get('date', ''))
            end_dt = event_data['end'].get('dateTime', event_data['end'].get('date', ''))

            event = CalendarEvent(
                title=event_data.get('summary', 'Untitled'),
                start=datetime.fromisoformat(start_dt.replace('Z', '+00:00')),
                end=datetime.fromisoformat(end_dt.replace('Z', '+00:00')),
                description=event_data.get('description', ''),
                event_id=event_data.get('id', '')
            )
            existing_events.append(event)

        # Parse preferences
        prefs = test_case.get('preferences', {})
        study_windows = prefs.get('study_windows', '9am-5pm')

        # Parse working hours from study_windows
        # Simple parser for formats like "9am-5pm" or "9:00-17:00"
        working_hours = self._parse_working_hours(study_windows)

        preferences = UserPreferences(
            working_hours=working_hours,
            max_daily_hours=float(prefs.get('max_daily_hours', 8)),
            buffer_minutes=15
        )

        return tasks, existing_events, preferences, test_case.get('preferences', {})

    def _parse_working_hours(self, study_windows: str) -> WorkingHours:
        """Parse working hours from study windows string.

        Args:
            study_windows: String like "9am-5pm" or "9:00-17:00"

        Returns:
            WorkingHours object
        """
        # Default to 9am-10pm
        default_start = time_type(9, 0)
        default_end = time_type(22, 0)

        if not study_windows:
            return WorkingHours(start=default_start, end=default_end)

        # Extract first time range (simplified)
        # Handle formats like "9am-5pm, 7pm-10pm" - take first range
        first_range = study_windows.split(',')[0].strip()

        # Try to extract times
        try:
            # Match patterns like "9am-5pm" or "09:00-17:00"
            parts = first_range.split('-')
            if len(parts) >= 2:
                start_str = parts[0].strip()
                end_str = parts[1].strip()

                start_time = self._parse_time(start_str)
                end_time = self._parse_time(end_str)

                if start_time and end_time:
                    return WorkingHours(start=start_time, end=end_time)
        except Exception:
            pass

        return WorkingHours(start=default_start, end=default_end)

    def _parse_time(self, time_str: str) -> Optional[time_type]:
        """Parse time from string.

        Args:
            time_str: Time string like "9am", "5pm", "09:00", "17:00"

        Returns:
            time object or None
        """
        time_str = time_str.strip().lower()

        # Try parsing "9am" or "5pm" format
        match = re.match(r'(\d+)([ap]m)', time_str)
        if match:
            hour = int(match.group(1))
            meridiem = match.group(2)

            if meridiem == 'pm' and hour != 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0

            return time_type(hour, 0)

        # Try parsing "09:00" or "17:00" format
        match = re.match(r'(\d+):(\d+)', time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            return time_type(hour, minute)

        return None

    def run_baseline(
        self,
        test_case: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], ScheduleMetrics]:
        """Run baseline greedy scheduler on a test case.

        Args:
            test_case: Test case dictionary

        Returns:
            Tuple of (scheduled_events, metrics)
        """
        start_time = time.time()

        # Parse test case
        tasks, existing_events, preferences, prefs_dict = self.parse_test_case(test_case)

        # Run baseline scheduler
        try:
            schedule = self.baseline_scheduler.generate_schedule(
                tasks, existing_events, preferences
            )

            # Convert to dict format
            scheduled_events = [
                {
                    'title': event.title,
                    'start': event.start.isoformat(),
                    'end': event.end.isoformat(),
                    'description': event.description or ''
                }
                for event in schedule.events
            ]

            latency = time.time() - start_time

            # Compute metrics
            metrics = compute_all_metrics(
                scheduled_events=scheduled_events,
                existing_events=[self._event_to_dict(e) for e in existing_events],
                tasks=[self._task_to_dict(t) for t in tasks],
                preferences=prefs_dict,
                parsing_success=True,
                latency_seconds=latency,
                model="baseline"
            )

            return scheduled_events, metrics

        except Exception as e:
            latency = time.time() - start_time
            metrics = ScheduleMetrics()
            metrics.parsing_success = False
            metrics.parse_error_message = str(e)
            metrics.latency_seconds = latency
            return [], metrics

    def run_llm_with_strategy(
        self,
        test_case: Dict[str, Any],
        strategy_name: str
    ) -> tuple[List[Dict[str, Any]], ScheduleMetrics]:
        """Run LLM scheduler with a specific prompting strategy.

        Args:
            test_case: Test case dictionary
            strategy_name: Name of prompting strategy to use

        Returns:
            Tuple of (scheduled_events, metrics)
        """
        start_time = time.time()

        # Parse test case
        tasks, existing_events, preferences, prefs_dict = self.parse_test_case(test_case)

        # Get prompting strategy
        strategy = get_strategy(strategy_name)

        # Build payload for prompts
        payload = {
            'preferences': prefs_dict,
            'existing_events': [self._event_to_dict(e) for e in existing_events],
            'new_tasks': [self._task_to_dict(t) for t in tasks]
        }

        # Get prompts
        system_prompt, user_prompt = strategy.build_prompts(payload)

        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4
            )

            result_text = response.choices[0].message.content.strip()
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

            # Parse JSON from response
            scheduled_events, parsing_success, parse_error = self._parse_llm_response(
                result_text
            )

            latency = time.time() - start_time

            # Compute metrics
            metrics = compute_all_metrics(
                scheduled_events=scheduled_events,
                existing_events=[self._event_to_dict(e) for e in existing_events],
                tasks=[self._task_to_dict(t) for t in tasks],
                preferences=prefs_dict,
                parsing_success=parsing_success,
                parse_error=parse_error,
                latency_seconds=latency,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=self.model
            )

            return scheduled_events, metrics

        except Exception as e:
            latency = time.time() - start_time
            metrics = ScheduleMetrics()
            metrics.parsing_success = False
            metrics.parse_error_message = str(e)
            metrics.latency_seconds = latency
            return [], metrics

    def _parse_llm_response(
        self,
        response_text: str
    ) -> tuple[List[Dict[str, Any]], bool, str]:
        """Parse LLM response to extract JSON schedule.

        Args:
            response_text: Raw LLM response

        Returns:
            Tuple of (scheduled_events, parsing_success, error_message)
        """
        # Remove markdown code fences
        cleaned = re.sub(
            r"^```(?:json)?|```$",
            "",
            response_text.strip(),
            flags=re.MULTILINE
        ).strip()

        # Try to find JSON array in the text
        # Look for content between [ and ]
        json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)

        try:
            events = json.loads(cleaned)
            if not isinstance(events, list):
                return [], False, "Response is not a JSON array"
            return events, True, ""
        except json.JSONDecodeError as e:
            return [], False, f"JSON parsing failed: {str(e)}"

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task object to dictionary."""
        return {
            'id': task.id,
            'name': task.name,
            'subject': task.subject,
            'estimated_hours': task.estimated_hours,
            'deadline': task.deadline.isoformat(),
            'priority': task.priority.value,
            'can_be_split': task.can_be_split
        }

    def _event_to_dict(self, event: CalendarEvent) -> Dict[str, Any]:
        """Convert CalendarEvent object to dictionary."""
        return {
            'title': event.title,
            'start': {'dateTime': event.start.isoformat()},
            'end': {'dateTime': event.end.isoformat()},
            'description': event.description or ''
        }

    def evaluate_all(
        self,
        test_cases: Optional[List[Dict[str, Any]]] = None,
        strategies: Optional[List[str]] = None,
        output_file: str = "evaluation/results.json"
    ) -> Dict[str, Any]:
        """Run full evaluation across all test cases and strategies.

        Args:
            test_cases: List of test cases (if None, loads from tests.json)
            strategies: List of strategy names to evaluate (if None, uses all)
            output_file: Path to save results JSON

        Returns:
            Dictionary containing all results
        """
        if test_cases is None:
            test_cases = self.load_test_cases()

        if strategies is None:
            strategies = list(list_strategies().keys())

        results = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'model': self.model,
                'num_test_cases': len(test_cases),
                'strategies': strategies
            },
            'results': []
        }

        print(f"Running evaluation on {len(test_cases)} test cases...")
        print(f"Strategies: {', '.join(strategies)}")
        print(f"Model: {self.model}\n")

        for i, test_case in enumerate(test_cases, 1):
            print(f"Test Case {i}/{len(test_cases)} (ID: {test_case.get('id', i)})")

            test_result = {
                'test_case_id': test_case.get('id', i),
                'split_type': test_case.get('split_type', 'unknown'),
                'feasibility': test_case.get('feasibility', 'unknown'),
                'num_tasks': len(test_case.get('new_tasks', [])),
                'baseline': {},
                'llm_strategies': {}
            }

            # Run baseline
            print(f"  Running baseline...")
            _, baseline_metrics = self.run_baseline(test_case)
            test_result['baseline'] = baseline_metrics.to_dict()

            # Run each LLM strategy
            for strategy_name in strategies:
                print(f"  Running {strategy_name}...")
                _, llm_metrics = self.run_llm_with_strategy(test_case, strategy_name)
                test_result['llm_strategies'][strategy_name] = llm_metrics.to_dict()

            results['results'].append(test_result)
            print()

        # Save results
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to {output_file}")

        return results

    def compute_aggregate_metrics(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute aggregate statistics across all test cases.

        Args:
            results: Results dictionary from evaluate_all()

        Returns:
            Dictionary of aggregate metrics per strategy
        """
        strategies = results['metadata']['strategies']

        aggregates = {
            'baseline': self._aggregate_metrics([
                r['baseline'] for r in results['results']
            ])
        }

        for strategy in strategies:
            strategy_metrics = [
                r['llm_strategies'][strategy]
                for r in results['results']
            ]
            aggregates[strategy] = self._aggregate_metrics(strategy_metrics)

        return aggregates

    def _aggregate_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute mean and std for numeric metrics.

        Args:
            metrics_list: List of metric dictionaries

        Returns:
            Dictionary of aggregated metrics
        """
        import numpy as np

        numeric_keys = [
            'deadline_compliance_rate', 'workload_variance',
            'average_daily_hours', 'completion_ratio',
            'fragmentation_score', 'makespan_days',
            'api_cost', 'latency_seconds', 'total_tokens'
        ]

        aggregates = {}

        for key in numeric_keys:
            values = [m[key] for m in metrics_list if key in m and m[key] is not None]
            if values:
                aggregates[f'{key}_mean'] = float(np.mean(values))
                aggregates[f'{key}_std'] = float(np.std(values))

        # Count-based metrics
        total_cases = len(metrics_list)
        aggregates['conflict_free_rate'] = sum(
            1 for m in metrics_list if m.get('conflict_free', False)
        ) / total_cases if total_cases > 0 else 0

        aggregates['parsing_success_rate'] = sum(
            1 for m in metrics_list if m.get('parsing_success', False)
        ) / total_cases if total_cases > 0 else 0

        return aggregates
