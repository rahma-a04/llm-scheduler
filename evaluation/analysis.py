"""
Analysis and visualization utilities for evaluation results.

Provides functions to analyze results, generate summary tables,
and create comparison plots.
"""

import json
from typing import Dict, Any, List
import numpy as np


def print_summary_table(results: Dict[str, Any]) -> None:
    """Print a formatted summary table of results.

    Args:
        results: Results dictionary from evaluation
    """
    strategies = results['metadata']['strategies']
    all_results = results['results']

    # Compute aggregates
    print("\n" + "=" * 100)
    print("SUMMARY METRICS (Mean ± Std)")
    print("=" * 100)

    # Header
    header = f"{'Strategy':<20} | {'Conflict-free %':<15} | {'Deadline %':<12} | {'Parse %':<10} | {'Workload Var':<12} | {'Cost ($)':<10}"
    print(header)
    print("-" * 100)

    # Baseline
    baseline_metrics = [r['baseline'] for r in all_results if r.get('baseline')]
    if baseline_metrics:
        print_strategy_row("Baseline", baseline_metrics)

    # Each LLM strategy
    for strategy in strategies:
        strategy_metrics = [
            r['llm_strategies'][strategy]
            for r in all_results
            if strategy in r.get('llm_strategies', {})
        ]
        if strategy_metrics:
            print_strategy_row(strategy, strategy_metrics)

    print("=" * 100)


def print_strategy_row(name: str, metrics_list: List[Dict[str, Any]]) -> None:
    """Print a single row of the summary table.

    Args:
        name: Strategy name
        metrics_list: List of metric dictionaries for this strategy
    """
    # Conflict-free rate
    conflict_free = [m.get('conflict_free', False) for m in metrics_list]
    conflict_rate = sum(conflict_free) / len(conflict_free) * 100 if conflict_free else 0

    # Deadline compliance
    deadline_vals = [m.get('deadline_compliance_rate', 0) for m in metrics_list]
    deadline_mean = np.mean(deadline_vals) * 100 if deadline_vals else 0
    deadline_std = np.std(deadline_vals) * 100 if deadline_vals else 0

    # Parsing success
    parse_success = [m.get('parsing_success', False) for m in metrics_list]
    parse_rate = sum(parse_success) / len(parse_success) * 100 if parse_success else 0

    # Workload variance
    workload_vals = [m.get('workload_variance', 0) for m in metrics_list if m.get('parsing_success', False)]
    workload_mean = np.mean(workload_vals) if workload_vals else 0
    workload_std = np.std(workload_vals) if workload_vals else 0

    # API cost
    cost_vals = [m.get('api_cost', 0) for m in metrics_list]
    cost_mean = np.mean(cost_vals) if cost_vals else 0
    cost_std = np.std(cost_vals) if cost_vals else 0

    row = (
        f"{name:<20} | "
        f"{conflict_rate:>14.1f}% | "
        f"{deadline_mean:>5.1f}±{deadline_std:>4.1f}% | "
        f"{parse_rate:>9.1f}% | "
        f"{workload_mean:>5.2f}±{workload_std:>4.2f} | "
        f"{cost_mean:>5.3f}±{cost_std:>3.3f}"
    )
    print(row)


def create_comparison_plots(
    results: Dict[str, Any],
    output_file: str = "evaluation/comparison.png"
) -> None:
    """Create comparison plots for different strategies.

    Args:
        results: Results dictionary from evaluation
        output_file: Output file path for plots
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")

    strategies = ['baseline'] + results['metadata']['strategies']
    all_results = results['results']

    # Prepare data
    data = {strategy: {
        'conflict_free': [],
        'deadline_compliance': [],
        'workload_variance': [],
        'api_cost': [],
        'completion_ratio': []
    } for strategy in strategies}

    for result in all_results:
        # Baseline
        if 'baseline' in result:
            m = result['baseline']
            data['baseline']['conflict_free'].append(1.0 if m.get('conflict_free', False) else 0.0)
            data['baseline']['deadline_compliance'].append(m.get('deadline_compliance_rate', 0))
            data['baseline']['workload_variance'].append(m.get('workload_variance', 0))
            data['baseline']['api_cost'].append(0)
            data['baseline']['completion_ratio'].append(m.get('completion_ratio', 0))

        # LLM strategies
        for strategy in results['metadata']['strategies']:
            if strategy in result.get('llm_strategies', {}):
                m = result['llm_strategies'][strategy]
                if m.get('parsing_success', False):
                    data[strategy]['conflict_free'].append(1.0 if m.get('conflict_free', False) else 0.0)
                    data[strategy]['deadline_compliance'].append(m.get('deadline_compliance_rate', 0))
                    data[strategy]['workload_variance'].append(m.get('workload_variance', 0))
                    data[strategy]['api_cost'].append(m.get('api_cost', 0))
                    data[strategy]['completion_ratio'].append(m.get('completion_ratio', 0))

    # Create subplots
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Scheduler Comparison Across Strategies', fontsize=16)

    # Plot 1: Conflict-free rate
    ax = axes[0, 0]
    conflict_rates = [np.mean(data[s]['conflict_free']) * 100 for s in strategies]
    ax.bar(range(len(strategies)), conflict_rates, color='skyblue')
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.set_ylabel('Rate (%)')
    ax.set_title('Conflict-Free Rate')
    ax.set_ylim([0, 105])

    # Plot 2: Deadline compliance
    ax = axes[0, 1]
    deadline_means = [np.mean(data[s]['deadline_compliance']) * 100 for s in strategies]
    deadline_stds = [np.std(data[s]['deadline_compliance']) * 100 for s in strategies]
    ax.bar(range(len(strategies)), deadline_means, yerr=deadline_stds, color='lightgreen', capsize=5)
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.set_ylabel('Rate (%)')
    ax.set_title('Deadline Compliance Rate')
    ax.set_ylim([0, 105])

    # Plot 3: Workload variance
    ax = axes[0, 2]
    workload_means = [np.mean(data[s]['workload_variance']) for s in strategies]
    workload_stds = [np.std(data[s]['workload_variance']) for s in strategies]
    ax.bar(range(len(strategies)), workload_means, yerr=workload_stds, color='lightcoral', capsize=5)
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.set_ylabel('Variance')
    ax.set_title('Workload Variance (lower is better)')

    # Plot 4: API cost
    ax = axes[1, 0]
    cost_means = [np.mean(data[s]['api_cost']) for s in strategies]
    cost_stds = [np.std(data[s]['api_cost']) for s in strategies]
    ax.bar(range(len(strategies)), cost_means, yerr=cost_stds, color='gold', capsize=5)
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.set_ylabel('Cost ($)')
    ax.set_title('Average API Cost per Test Case')

    # Plot 5: Completion ratio
    ax = axes[1, 1]
    completion_means = [np.mean(data[s]['completion_ratio']) * 100 for s in strategies]
    completion_stds = [np.std(data[s]['completion_ratio']) * 100 for s in strategies]
    ax.bar(range(len(strategies)), completion_means, yerr=completion_stds, color='plum', capsize=5)
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.set_ylabel('Rate (%)')
    ax.set_title('Completion Ratio')
    ax.set_ylim([0, 105])

    # Plot 6: Cost vs Quality tradeoff
    ax = axes[1, 2]
    for i, strategy in enumerate(strategies):
        if strategy != 'baseline':
            quality_score = (
                np.mean(data[strategy]['conflict_free']) +
                np.mean(data[strategy]['deadline_compliance'])
            ) / 2 * 100
            cost = np.mean(data[strategy]['api_cost'])
            ax.scatter(cost, quality_score, s=100, label=strategy)

    ax.set_xlabel('API Cost ($)')
    ax.set_ylabel('Quality Score (%)')
    ax.set_title('Cost vs Quality Tradeoff')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


def generate_latex_table(results: Dict[str, Any]) -> str:
    """Generate LaTeX table code for results.

    Args:
        results: Results dictionary from evaluation

    Returns:
        LaTeX table code as string
    """
    strategies = ['baseline'] + results['metadata']['strategies']
    all_results = results['results']

    latex = "\\begin{table}[h]\n"
    latex += "\\centering\n"
    latex += "\\begin{tabular}{lcccccc}\n"
    latex += "\\hline\n"
    latex += "Strategy & Conflict-free \\% & Deadline \\% & Parse \\% & Workload Var & Cost (\\$) \\\\\n"
    latex += "\\hline\n"

    for strategy in strategies:
        if strategy == 'baseline':
            metrics_list = [r['baseline'] for r in all_results if r.get('baseline')]
        else:
            metrics_list = [
                r['llm_strategies'][strategy]
                for r in all_results
                if strategy in r.get('llm_strategies', {})
            ]

        if not metrics_list:
            continue

        # Compute statistics
        conflict_free = [m.get('conflict_free', False) for m in metrics_list]
        conflict_rate = sum(conflict_free) / len(conflict_free) * 100

        deadline_vals = [m.get('deadline_compliance_rate', 0) for m in metrics_list]
        deadline_mean = np.mean(deadline_vals) * 100

        parse_success = [m.get('parsing_success', False) for m in metrics_list]
        parse_rate = sum(parse_success) / len(parse_success) * 100

        workload_vals = [m.get('workload_variance', 0) for m in metrics_list if m.get('parsing_success', False)]
        workload_mean = np.mean(workload_vals) if workload_vals else 0

        cost_vals = [m.get('api_cost', 0) for m in metrics_list]
        cost_mean = np.mean(cost_vals)

        latex += f"{strategy.replace('_', ' ').title()} & "
        latex += f"{conflict_rate:.1f} & {deadline_mean:.1f} & {parse_rate:.1f} & "
        latex += f"{workload_mean:.2f} & {cost_mean:.3f} \\\\\n"

    latex += "\\hline\n"
    latex += "\\end{tabular}\n"
    latex += "\\caption{Comparison of scheduling strategies across evaluation metrics}\n"
    latex += "\\label{tab:results}\n"
    latex += "\\end{table}\n"

    return latex


def save_latex_table(results: Dict[str, Any], output_file: str = "evaluation/results_table.tex") -> None:
    """Save LaTeX table to file.

    Args:
        results: Results dictionary from evaluation
        output_file: Output file path
    """
    latex = generate_latex_table(results)
    with open(output_file, 'w') as f:
        f.write(latex)
    print(f"LaTeX table saved to {output_file}")
