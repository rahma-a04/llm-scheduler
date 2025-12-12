#!/usr/bin/env python3
"""
Main evaluation script for LLM scheduler comparison.

Usage:
    python evaluation/run_evaluation.py --api-key YOUR_API_KEY
    python evaluation/run_evaluation.py --api-key YOUR_API_KEY --strategies zero_shot few_shot
    python evaluation/run_evaluation.py --api-key YOUR_API_KEY --output my_results.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.evaluator import Evaluator
from evaluation.prompts import list_strategies
from evaluation.analysis import print_summary_table, create_comparison_plots


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate LLM scheduling strategies against baseline"
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API key (or set OPENAI_API_KEY environment variable)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o',
        help='OpenAI model to use (default: gpt-4o)'
    )

    parser.add_argument(
        '--test-file',
        type=str,
        default='evaluation/tests.json',
        help='Path to test cases JSON file (default: evaluation/tests.json)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file for results (default: evaluation/results_TIMESTAMP.json)'
    )

    parser.add_argument(
        '--strategies',
        nargs='+',
        default=None,
        help=f'Strategies to evaluate (default: all). Options: {", ".join(list_strategies().keys())}'
    )

    parser.add_argument(
        '--num-cases',
        type=int,
        default=None,
        help='Number of test cases to run (default: all)'
    )

    parser.add_argument(
        '--skip-baseline',
        action='store_true',
        help='Skip baseline evaluation (only run LLM strategies)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed output'
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OpenAI API key required. Use --api-key or set OPENAI_API_KEY environment variable.")
        sys.exit(1)

    # Set output file
    if args.output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'evaluation/results_{timestamp}.json'

    # Print configuration
    print("=" * 70)
    print("LLM Scheduler Evaluation")
    print("=" * 70)
    print(f"Model: {args.model}")
    print(f"Test file: {args.test_file}")
    print(f"Output: {args.output}")

    # Initialize evaluator
    evaluator = Evaluator(api_key, model=args.model)

    # Load test cases
    try:
        test_cases = evaluator.load_test_cases(args.test_file)
    except FileNotFoundError:
        print(f"Error: Test file not found: {args.test_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in test file: {e}")
        sys.exit(1)

    # Limit number of test cases if specified
    if args.num_cases:
        test_cases = test_cases[:args.num_cases]
        print(f"Running on first {args.num_cases} test cases")

    # Get strategies to evaluate
    strategies = args.strategies
    if strategies is None:
        strategies = list(list_strategies().keys())

    print(f"Strategies: {', '.join(strategies)}")
    print(f"Test cases: {len(test_cases)}")
    print("=" * 70)
    print()

    # Run evaluation
    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'model': args.model,
            'num_test_cases': len(test_cases),
            'strategies': strategies,
            'skip_baseline': args.skip_baseline
        },
        'results': []
    }

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}/{len(test_cases)} (ID: {test_case.get('id', i)})")
        print(f"  Split: {test_case.get('split_type', 'unknown')}, "
              f"Feasibility: {test_case.get('feasibility', 'unknown')}, "
              f"Tasks: {len(test_case.get('new_tasks', []))}")

        test_result = {
            'test_case_id': test_case.get('id', i),
            'split_type': test_case.get('split_type', 'unknown'),
            'feasibility': test_case.get('feasibility', 'unknown'),
            'num_tasks': len(test_case.get('new_tasks', [])),
            'baseline': {},
            'llm_strategies': {}
        }

        # Run baseline
        if not args.skip_baseline:
            print(f"  Running baseline...", end='', flush=True)
            try:
                _, baseline_metrics = evaluator.run_baseline(test_case)
                test_result['baseline'] = baseline_metrics.to_dict()
                print(f" ✓ (conflicts: {baseline_metrics.num_conflicts}, "
                      f"deadline: {baseline_metrics.deadline_compliance_rate:.1%})")
            except Exception as e:
                print(f" ✗ Error: {str(e)}")
                test_result['baseline']['error'] = str(e)

        # Run each LLM strategy
        for strategy_name in strategies:
            print(f"  Running {strategy_name}...", end='', flush=True)
            try:
                _, llm_metrics = evaluator.run_llm_with_strategy(test_case, strategy_name)
                test_result['llm_strategies'][strategy_name] = llm_metrics.to_dict()

                if llm_metrics.parsing_success:
                    print(f" ✓ (conflicts: {llm_metrics.num_conflicts}, "
                          f"deadline: {llm_metrics.deadline_compliance_rate:.1%}, "
                          f"cost: ${llm_metrics.api_cost:.4f})")
                else:
                    print(f" ✗ Parsing failed: {llm_metrics.parse_error_message[:50]}")
            except Exception as e:
                print(f" ✗ Error: {str(e)}")
                test_result['llm_strategies'][strategy_name] = {'error': str(e)}

        results['results'].append(test_result)
        print()

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"Results saved to {args.output}")
    print("=" * 70)
    print()

    # Compute and display aggregate metrics
    print_summary_table(results)

    # Optionally create plots
    try:
        plot_file = str(output_path.with_suffix('.png'))
        create_comparison_plots(results, output_file=plot_file)
        print(f"\nComparison plots saved to {plot_file}")
    except Exception as e:
        print(f"\nNote: Could not create plots: {e}")
        print("Install matplotlib to enable plot generation: pip install matplotlib")

    print("\nEvaluation complete!")


if __name__ == '__main__':
    main()
