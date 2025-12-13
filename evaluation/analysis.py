"""
Analysis and visualization utilities for evaluation results.

Provides functions to analyze results, generate summary tables,
and create comparison plots.
"""

import json
from typing import Dict, Any, List
import numpy as np


def print_summary_table(results: Dict[str, Any], save_csv: bool = True) -> None:
    """Print a comprehensive formatted summary table of results.

    Args:
        results: Results dictionary from evaluation
        save_csv: Whether to save results to CSV file
    """
    strategies = results['metadata']['strategies']
    all_results = results['results']

    # Compute aggregates
    print("\n" + "=" * 180)
    print("COMPREHENSIVE SUMMARY METRICS (Mean ± Std)")
    print("=" * 180)

    # Table 1: Constraint & Correctness Metrics
    print("\n--- CONSTRAINT & CORRECTNESS METRICS ---")
    header = f"{'Strategy':<20} | {'Conflict-free %':<15} | {'Deadline %':<15} | {'Parse %':<12} | {'Fully Sched':<12} | {'Partial':<10} | {'Unsched':<10}"
    print(header)
    print("-" * 120)

    # Baseline
    baseline_metrics = [r['baseline'] for r in all_results if r.get('baseline')]
    if baseline_metrics:
        print_constraint_row("Baseline", baseline_metrics)

    # Each LLM strategy
    for strategy in strategies:
        strategy_metrics = [
            r['llm_strategies'][strategy]
            for r in all_results
            if strategy in r.get('llm_strategies', {})
        ]
        if strategy_metrics:
            print_constraint_row(strategy, strategy_metrics)

    # Table 2: Quality & System Metrics
    print("\n--- QUALITY & SYSTEM METRICS ---")
    header = f"{'Strategy':<20} | {'Workload Var':<15} | {'Completion %':<15} | {'Frag Score':<12} | {'Makespan':<12} | {'Cost ($)':<12} | {'Latency (s)':<12}"
    print(header)
    print("-" * 130)

    if baseline_metrics:
        print_quality_row("Baseline", baseline_metrics)

    for strategy in strategies:
        strategy_metrics = [
            r['llm_strategies'][strategy]
            for r in all_results
            if strategy in r.get('llm_strategies', {})
        ]
        if strategy_metrics:
            print_quality_row(strategy, strategy_metrics)

    # Table 3: LLM Evaluation Metrics (if available)
    has_llm_eval = any(
        m.get('llm_quality_score', 0) > 0
        for r in all_results
        for m in [r.get('baseline', {})] + list(r.get('llm_strategies', {}).values())
    )

    if has_llm_eval:
        print("\n--- LLM-BASED EVALUATION METRICS ---")
        header = f"{'Strategy':<20} | {'Quality Score':<15} | {'Preference Score':<18}"
        print(header)
        print("-" * 60)

        if baseline_metrics:
            print_llm_eval_row("Baseline", baseline_metrics)

        for strategy in strategies:
            strategy_metrics = [
                r['llm_strategies'][strategy]
                for r in all_results
                if strategy in r.get('llm_strategies', {})
            ]
            if strategy_metrics:
                print_llm_eval_row(strategy, strategy_metrics)

    print("=" * 180)

    # Save to CSV if requested
    if save_csv:
        save_summary_csv(results, "evaluation/summary_statistics.csv")


def print_constraint_row(name: str, metrics_list: List[Dict[str, Any]]) -> None:
    """Print constraint & correctness metrics row.

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

    # Task scheduling breakdown
    fully_vals = [m.get('tasks_fully_scheduled', 0) for m in metrics_list]
    partial_vals = [m.get('tasks_partially_scheduled', 0) for m in metrics_list]
    unsched_vals = [m.get('tasks_unscheduled', 0) for m in metrics_list]

    fully_mean = np.mean(fully_vals) if fully_vals else 0
    partial_mean = np.mean(partial_vals) if partial_vals else 0
    unsched_mean = np.mean(unsched_vals) if unsched_vals else 0

    row = (
        f"{name:<20} | "
        f"{conflict_rate:>14.1f}% | "
        f"{deadline_mean:>6.1f}±{deadline_std:>5.1f}% | "
        f"{parse_rate:>11.1f}% | "
        f"{fully_mean:>11.1f} | "
        f"{partial_mean:>9.1f} | "
        f"{unsched_mean:>9.1f}"
    )
    print(row)


def print_quality_row(name: str, metrics_list: List[Dict[str, Any]]) -> None:
    """Print quality & system metrics row.

    Args:
        name: Strategy name
        metrics_list: List of metric dictionaries for this strategy
    """
    # Workload variance
    workload_vals = [m.get('workload_variance', 0) for m in metrics_list if m.get('parsing_success', False)]
    workload_mean = np.mean(workload_vals) if workload_vals else 0
    workload_std = np.std(workload_vals) if workload_vals else 0

    # Completion ratio
    completion_vals = [m.get('completion_ratio', 0) * 100 for m in metrics_list if m.get('parsing_success', False)]
    completion_mean = np.mean(completion_vals) if completion_vals else 0
    completion_std = np.std(completion_vals) if completion_vals else 0

    # Fragmentation score
    frag_vals = [m.get('fragmentation_score', 0) for m in metrics_list if m.get('parsing_success', False)]
    frag_mean = np.mean(frag_vals) if frag_vals else 0
    frag_std = np.std(frag_vals) if frag_vals else 0

    # Makespan
    makespan_vals = [m.get('makespan_days', 0) for m in metrics_list if m.get('parsing_success', False)]
    makespan_mean = np.mean(makespan_vals) if makespan_vals else 0
    makespan_std = np.std(makespan_vals) if makespan_vals else 0

    # API cost
    cost_vals = [m.get('api_cost', 0) for m in metrics_list]
    cost_mean = np.mean(cost_vals) if cost_vals else 0
    cost_std = np.std(cost_vals) if cost_vals else 0

    # Latency
    latency_vals = [m.get('latency_seconds', 0) for m in metrics_list]
    latency_mean = np.mean(latency_vals) if latency_vals else 0
    latency_std = np.std(latency_vals) if latency_vals else 0

    row = (
        f"{name:<20} | "
        f"{workload_mean:>6.2f}±{workload_std:>5.2f} | "
        f"{completion_mean:>6.1f}±{completion_std:>5.1f}% | "
        f"{frag_mean:>5.2f}±{frag_std:>3.2f} | "
        f"{makespan_mean:>5.1f}±{makespan_std:>3.1f} | "
        f"{cost_mean:>5.3f}±{cost_std:>3.3f} | "
        f"{latency_mean:>5.2f}±{latency_std:>3.2f}"
    )
    print(row)


def print_llm_eval_row(name: str, metrics_list: List[Dict[str, Any]]) -> None:
    """Print LLM evaluation metrics row.

    Args:
        name: Strategy name
        metrics_list: List of metric dictionaries for this strategy
    """
    # LLM quality score
    quality_vals = [m.get('llm_quality_score', 0) for m in metrics_list if m.get('llm_quality_score', 0) > 0]
    quality_mean = np.mean(quality_vals) if quality_vals else 0
    quality_std = np.std(quality_vals) if quality_vals else 0

    # LLM preference score
    pref_vals = [m.get('llm_preference_score', 0) for m in metrics_list if m.get('llm_preference_score', 0) > 0]
    pref_mean = np.mean(pref_vals) if pref_vals else 0
    pref_std = np.std(pref_vals) if pref_vals else 0

    quality_str = f"{quality_mean:>5.1f}±{quality_std:>5.1f}" if quality_vals else "N/A".center(15)
    pref_str = f"{pref_mean:>5.1f}±{pref_std:>5.1f}" if pref_vals else "N/A".center(18)

    row = f"{name:<20} | {quality_str} | {pref_str}"
    print(row)


def save_summary_csv(results: Dict[str, Any], output_file: str = "evaluation/summary_statistics.csv") -> None:
    """Save comprehensive summary statistics to CSV file.

    Args:
        results: Results dictionary from evaluation
        output_file: Output file path for CSV
    """
    import csv

    strategies = ['baseline'] + results['metadata']['strategies']
    all_results = results['results']

    # Open CSV file for writing
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'Strategy',
            'Conflict-free %', 'Deadline Compliance %', 'Parse Success %',
            'Tasks Fully Scheduled', 'Tasks Partially Scheduled', 'Tasks Unscheduled',
            'Workload Variance', 'Completion Ratio %', 'Fragmentation Score',
            'Makespan (days)', 'API Cost ($)', 'Latency (s)',
            'LLM Quality Score', 'LLM Preference Score'
        ])

        # Write data for each strategy
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

            # Compute all statistics
            conflict_free = [m.get('conflict_free', False) for m in metrics_list]
            conflict_rate = sum(conflict_free) / len(conflict_free) * 100

            deadline_vals = [m.get('deadline_compliance_rate', 0) for m in metrics_list]
            deadline_mean = np.mean(deadline_vals) * 100

            parse_success = [m.get('parsing_success', False) for m in metrics_list]
            parse_rate = sum(parse_success) / len(parse_success) * 100

            fully_mean = np.mean([m.get('tasks_fully_scheduled', 0) for m in metrics_list])
            partial_mean = np.mean([m.get('tasks_partially_scheduled', 0) for m in metrics_list])
            unsched_mean = np.mean([m.get('tasks_unscheduled', 0) for m in metrics_list])

            workload_vals = [m.get('workload_variance', 0) for m in metrics_list if m.get('parsing_success', False)]
            workload_mean = np.mean(workload_vals) if workload_vals else 0

            completion_vals = [m.get('completion_ratio', 0) * 100 for m in metrics_list if m.get('parsing_success', False)]
            completion_mean = np.mean(completion_vals) if completion_vals else 0

            frag_vals = [m.get('fragmentation_score', 0) for m in metrics_list if m.get('parsing_success', False)]
            frag_mean = np.mean(frag_vals) if frag_vals else 0

            makespan_vals = [m.get('makespan_days', 0) for m in metrics_list if m.get('parsing_success', False)]
            makespan_mean = np.mean(makespan_vals) if makespan_vals else 0

            cost_mean = np.mean([m.get('api_cost', 0) for m in metrics_list])
            latency_mean = np.mean([m.get('latency_seconds', 0) for m in metrics_list])

            quality_vals = [m.get('llm_quality_score', 0) for m in metrics_list if m.get('llm_quality_score', 0) > 0]
            quality_mean = np.mean(quality_vals) if quality_vals else 0

            pref_vals = [m.get('llm_preference_score', 0) for m in metrics_list if m.get('llm_preference_score', 0) > 0]
            pref_mean = np.mean(pref_vals) if pref_vals else 0

            # Write row
            writer.writerow([
                strategy,
                f"{conflict_rate:.2f}", f"{deadline_mean:.2f}", f"{parse_rate:.2f}",
                f"{fully_mean:.2f}", f"{partial_mean:.2f}", f"{unsched_mean:.2f}",
                f"{workload_mean:.3f}", f"{completion_mean:.2f}", f"{frag_mean:.3f}",
                f"{makespan_mean:.2f}", f"{cost_mean:.4f}", f"{latency_mean:.3f}",
                f"{quality_mean:.2f}", f"{pref_mean:.2f}"
            ])

    print(f"\n✓ Summary statistics saved to {output_file}")


def create_comparison_plots(
    results: Dict[str, Any],
    output_dir: str = "evaluation/plots"
) -> None:
    """Create separate comparison plots for different strategies.

    Creates individual PNG files for each metric instead of a single subplot.

    Args:
        results: Results dictionary from evaluation
        output_dir: Output directory for plot files
    """
    try:
        import matplotlib.pyplot as plt
        import os
    except ImportError:
        raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    strategies = ['baseline'] + results['metadata']['strategies']
    all_results = results['results']

    # Prepare data
    data = {strategy: {
        'conflict_free': [],
        'deadline_compliance': [],
        'workload_variance': [],
        'api_cost': [],
        'completion_ratio': [],
        'fragmentation': [],
        'makespan': []
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
            data['baseline']['fragmentation'].append(m.get('fragmentation_score', 0))
            data['baseline']['makespan'].append(m.get('makespan_days', 0))

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
                    data[strategy]['fragmentation'].append(m.get('fragmentation_score', 0))
                    data[strategy]['makespan'].append(m.get('makespan_days', 0))

    plot_files = []

    # Plot 1: Conflict-free rate
    plt.figure(figsize=(10, 6))
    conflict_rates = [np.mean(data[s]['conflict_free']) * 100 for s in strategies]
    plt.bar(range(len(strategies)), conflict_rates, color='skyblue', edgecolor='navy', alpha=0.7)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Rate (%)', fontsize=12)
    plt.title('Conflict-Free Rate by Strategy', fontsize=14, fontweight='bold')
    plt.ylim([0, 105])
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file1 = f"{output_dir}/01_conflict_free_rate.png"
    plt.savefig(file1, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file1)

    # Plot 2: Deadline compliance
    plt.figure(figsize=(10, 6))
    deadline_means = [np.mean(data[s]['deadline_compliance']) * 100 for s in strategies]
    deadline_stds = [np.std(data[s]['deadline_compliance']) * 100 for s in strategies]
    plt.bar(range(len(strategies)), deadline_means, yerr=deadline_stds, color='lightgreen',
            edgecolor='darkgreen', alpha=0.7, capsize=5)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Rate (%)', fontsize=12)
    plt.title('Deadline Compliance Rate by Strategy', fontsize=14, fontweight='bold')
    plt.ylim([0, 105])
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file2 = f"{output_dir}/02_deadline_compliance.png"
    plt.savefig(file2, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file2)

    # Plot 3: Workload variance
    plt.figure(figsize=(10, 6))
    workload_means = [np.mean(data[s]['workload_variance']) for s in strategies]
    workload_stds = [np.std(data[s]['workload_variance']) for s in strategies]
    plt.bar(range(len(strategies)), workload_means, yerr=workload_stds, color='lightcoral',
            edgecolor='darkred', alpha=0.7, capsize=5)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Variance (hours²)', fontsize=12)
    plt.title('Workload Variance by Strategy (lower is better)', fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file3 = f"{output_dir}/03_workload_variance.png"
    plt.savefig(file3, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file3)

    # Plot 4: API cost
    plt.figure(figsize=(10, 6))
    cost_means = [np.mean(data[s]['api_cost']) for s in strategies]
    cost_stds = [np.std(data[s]['api_cost']) for s in strategies]
    plt.bar(range(len(strategies)), cost_means, yerr=cost_stds, color='gold',
            edgecolor='orange', alpha=0.7, capsize=5)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Cost ($)', fontsize=12)
    plt.title('Average API Cost per Test Case', fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file4 = f"{output_dir}/04_api_cost.png"
    plt.savefig(file4, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file4)

    # Plot 5: Completion ratio
    plt.figure(figsize=(10, 6))
    completion_means = [np.mean(data[s]['completion_ratio']) * 100 for s in strategies]
    completion_stds = [np.std(data[s]['completion_ratio']) * 100 for s in strategies]
    plt.bar(range(len(strategies)), completion_means, yerr=completion_stds, color='plum',
            edgecolor='purple', alpha=0.7, capsize=5)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Rate (%)', fontsize=12)
    plt.title('Task Completion Ratio by Strategy', fontsize=14, fontweight='bold')
    plt.ylim([0, 105])
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file5 = f"{output_dir}/05_completion_ratio.png"
    plt.savefig(file5, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file5)

    # Plot 6: Fragmentation score
    plt.figure(figsize=(10, 6))
    frag_means = [np.mean(data[s]['fragmentation']) for s in strategies]
    frag_stds = [np.std(data[s]['fragmentation']) for s in strategies]
    plt.bar(range(len(strategies)), frag_means, yerr=frag_stds, color='lightsalmon',
            edgecolor='darkorange', alpha=0.7, capsize=5)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Avg Blocks per Task', fontsize=12)
    plt.title('Task Fragmentation by Strategy', fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file6 = f"{output_dir}/06_fragmentation.png"
    plt.savefig(file6, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file6)

    # Plot 7: Makespan
    plt.figure(figsize=(10, 6))
    makespan_means = [np.mean(data[s]['makespan']) for s in strategies]
    makespan_stds = [np.std(data[s]['makespan']) for s in strategies]
    plt.bar(range(len(strategies)), makespan_means, yerr=makespan_stds, color='lightsteelblue',
            edgecolor='steelblue', alpha=0.7, capsize=5)
    plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
    plt.ylabel('Days', fontsize=12)
    plt.title('Schedule Makespan by Strategy', fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    file7 = f"{output_dir}/07_makespan.png"
    plt.savefig(file7, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file7)

    # Plot 8: Cost vs Quality tradeoff
    plt.figure(figsize=(10, 6))
    for strategy in strategies:
        if strategy != 'baseline':
            quality_score = (
                np.mean(data[strategy]['conflict_free']) +
                np.mean(data[strategy]['deadline_compliance'])
            ) / 2 * 100
            cost = np.mean(data[strategy]['api_cost'])
            plt.scatter(cost, quality_score, s=150, label=strategy, alpha=0.7)
            plt.annotate(strategy, (cost, quality_score), xytext=(5, 5),
                        textcoords='offset points', fontsize=9)

    plt.xlabel('API Cost ($)', fontsize=12)
    plt.ylabel('Quality Score (%)', fontsize=12)
    plt.title('Cost vs Quality Tradeoff', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    file8 = f"{output_dir}/08_cost_vs_quality.png"
    plt.savefig(file8, dpi=300, bbox_inches='tight')
    plt.close()
    plot_files.append(file8)

    print(f"\n✓ Created {len(plot_files)} comparison plots in {output_dir}/")
    for pf in plot_files:
        print(f"  - {os.path.basename(pf)}")


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
