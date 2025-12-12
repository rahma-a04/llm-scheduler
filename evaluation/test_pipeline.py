#!/usr/bin/env python3
"""
Test script to verify the evaluation pipeline is working correctly.

This script tests the baseline scheduler without making API calls.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.evaluator import Evaluator
from evaluation.metrics import compute_all_metrics
import json


def test_load_test_cases():
    """Test loading test cases."""
    print("Testing: Load test cases...")

    evaluator = Evaluator(openai_api_key="dummy-key")  # Won't be used for baseline
    test_cases = evaluator.load_test_cases()

    assert len(test_cases) == 30, f"Expected 30 test cases, got {len(test_cases)}"
    assert 'new_tasks' in test_cases[0], "Test case missing 'new_tasks'"
    assert 'existing_events' in test_cases[0], "Test case missing 'existing_events'"
    assert 'preferences' in test_cases[0], "Test case missing 'preferences'"

    print(f"  ✓ Loaded {len(test_cases)} test cases")


def test_parse_test_case():
    """Test parsing test case into model objects."""
    print("Testing: Parse test case...")

    evaluator = Evaluator(openai_api_key="dummy-key")
    test_cases = evaluator.load_test_cases()
    test_case = test_cases[0]

    tasks, existing_events, preferences, prefs_dict = evaluator.parse_test_case(test_case)

    assert len(tasks) > 0, "No tasks parsed"
    assert all(hasattr(t, 'name') for t in tasks), "Tasks missing 'name' attribute"
    assert hasattr(preferences, 'working_hours'), "Preferences missing 'working_hours'"

    print(f"  ✓ Parsed {len(tasks)} tasks, {len(existing_events)} events")


def test_baseline_scheduler():
    """Test baseline scheduler on first test case."""
    print("Testing: Baseline scheduler...")

    evaluator = Evaluator(openai_api_key="dummy-key")
    test_cases = evaluator.load_test_cases()
    test_case = test_cases[0]

    scheduled_events, metrics = evaluator.run_baseline(test_case)

    assert metrics.parsing_success, "Baseline should always parse successfully"
    assert isinstance(scheduled_events, list), "Scheduled events should be a list"

    print(f"  ✓ Baseline scheduled {len(scheduled_events)} events")
    print(f"    - Conflicts: {metrics.num_conflicts}")
    print(f"    - Deadline compliance: {metrics.deadline_compliance_rate:.1%}")
    print(f"    - Completion ratio: {metrics.completion_ratio:.1%}")


def test_metrics_computation():
    """Test metrics computation."""
    print("Testing: Metrics computation...")

    # Create dummy data
    scheduled_events = [
        {
            'title': 'Task 1',
            'start': '2025-12-15T09:00:00',
            'end': '2025-12-15T10:30:00',
            'description': 'Test'
        },
        {
            'title': 'Task 1',
            'start': '2025-12-15T14:00:00',
            'end': '2025-12-15T15:00:00',
            'description': 'Test'
        }
    ]

    existing_events = [
        {
            'title': 'Existing Event',
            'start': {'dateTime': '2025-12-15T11:00:00'},
            'end': {'dateTime': '2025-12-15T12:00:00'},
            'description': 'Existing'
        }
    ]

    tasks = [
        {
            'id': 1,
            'name': 'Task 1',
            'estimated_hours': 2.5,
            'deadline': '2025-12-20'
        }
    ]

    preferences = {
        'study_windows': '9am-5pm',
        'max_daily_hours': 6,
        'additional_notes': ''
    }

    metrics = compute_all_metrics(
        scheduled_events=scheduled_events,
        existing_events=existing_events,
        tasks=tasks,
        preferences=preferences,
        parsing_success=True
    )

    assert metrics.conflict_free, "Should have no conflicts"
    assert metrics.total_tasks == 1, "Should count 1 task"
    assert metrics.hours_scheduled == 2.5, f"Should schedule 2.5 hours, got {metrics.hours_scheduled}"

    print(f"  ✓ Metrics computed successfully")
    print(f"    - Conflict-free: {metrics.conflict_free}")
    print(f"    - Hours scheduled: {metrics.hours_scheduled}")
    print(f"    - Workload variance: {metrics.workload_variance:.2f}")


def test_strategies_available():
    """Test that all strategies are available."""
    print("Testing: Prompting strategies...")

    from evaluation.prompts import list_strategies, get_strategy

    strategies = list_strategies()
    expected_strategies = ['zero_shot', 'few_shot', 'chain_of_thought', 'constraint_first']

    for strategy_name in expected_strategies:
        assert strategy_name in strategies, f"Strategy '{strategy_name}' not found"
        strategy = get_strategy(strategy_name)
        assert hasattr(strategy, 'build_prompts'), f"Strategy {strategy_name} missing build_prompts method"

    print(f"  ✓ All {len(strategies)} strategies available")
    for name, desc in strategies.items():
        print(f"    - {name}: {desc}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Evaluation Pipeline Test Suite")
    print("=" * 70)
    print()

    tests = [
        test_load_test_cases,
        test_parse_test_case,
        test_baseline_scheduler,
        test_metrics_computation,
        test_strategies_available,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            failed += 1
            print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed! The evaluation pipeline is ready to use.")
        print("\nNext steps:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Run: python evaluation/run_evaluation.py --num-cases 1")
        print("3. Once verified, run full evaluation: python evaluation/run_evaluation.py")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
