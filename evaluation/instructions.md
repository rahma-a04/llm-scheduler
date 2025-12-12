# LLM Scheduler Evaluation - Setup and Usage Instructions

This guide provides complete instructions for installing dependencies, configuring the evaluation environment, and running the evaluation pipeline for the LLM scheduler project.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Evaluation](#running-the-evaluation)
5. [Understanding the Results](#understanding-the-results)
6. [Customization](#customization)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.9 or higher** installed
- An **OpenAI API key** (for LLM-based evaluation)
- Basic familiarity with command-line interfaces
- Approximately **500 MB** of free disk space

---

## Installation

### 1. Clone or Navigate to the Project Directory

```bash
cd /Users/rahmaa/school/cs4701/llm-scheduler
```

### 2. Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

All required dependencies are listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

This will install:
- `openai` - OpenAI API client
- `jsonschema` - JSON validation
- `numpy` - Numerical computations for metrics
- `google-api-python-client` - Google Calendar integration
- All other project dependencies

### 4. Install Optional Dependencies for Visualization

For generating comparison plots:

```bash
pip install matplotlib
```

---

## Configuration

### 1. Set Up Your OpenAI API Key

You have two options:

**Option A: Environment Variable (Recommended)**

Add to your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

Then reload:

```bash
source ~/.zshrc  # or ~/.bashrc
```

**Option B: Pass as Command-Line Argument**

```bash
python evaluation/run_evaluation.py --api-key sk-your-api-key-here
```

### 2. Verify Test Cases

Ensure the test cases file exists:

```bash
ls -lh evaluation/tests.json
```

You should see a JSON file containing 30 test cases (approximately 75 KB).

### 3. Check Project Structure

Your evaluation directory should look like this:

```
evaluation/
├── tests.json           # 30 test cases
├── prompts.py           # 4 prompting strategies
├── metrics.py           # Metrics computation
├── evaluator.py         # Main evaluation pipeline
├── run_evaluation.py    # CLI script
├── analysis.py          # Results analysis and visualization
├── prompts.md           # Original prompt documentation
└── instructions.md      # This file
```

---

## Running the Evaluation

### Basic Usage

Run the full evaluation on all 30 test cases with all 4 strategies:

```bash
python evaluation/run_evaluation.py
```

This will:
1. Load all 30 test cases from `evaluation/tests.json`
2. Run the baseline greedy scheduler on each case
3. Run all 4 LLM prompting strategies on each case
4. Compute evaluation metrics for each run
5. Save results to `evaluation/results_TIMESTAMP.json`
6. Display a summary table

**Expected runtime:** Approximately 5-10 minutes (depends on API latency)

### Run with Specific Strategies

Evaluate only specific prompting strategies:

```bash
python evaluation/run_evaluation.py --strategies zero_shot few_shot
```

Available strategies:
- `zero_shot` - Direct zero-shot prompting
- `few_shot` - Few-shot learning with examples
- `chain_of_thought` - Chain-of-thought reasoning
- `constraint_first` - Constraint-first approach

### Run on a Subset of Test Cases

Test on the first 5 cases (useful for debugging):

```bash
python evaluation/run_evaluation.py --num-cases 5
```

### Specify Output File

```bash
python evaluation/run_evaluation.py --output my_results.json
```

### Skip Baseline (LLM-only evaluation)

```bash
python evaluation/run_evaluation.py --skip-baseline
```

### Use a Different Model

```bash
python evaluation/run_evaluation.py --model gpt-4
```

### All Options Combined

```bash
python evaluation/run_evaluation.py \
    --api-key sk-your-key \
    --model gpt-4o \
    --strategies zero_shot few_shot \
    --num-cases 10 \
    --output results_experiment1.json \
    --verbose
```

---

## Understanding the Results

### Output Files

After running the evaluation, you'll get:

1. **Results JSON** (`evaluation/results_TIMESTAMP.json`)
   - Contains all raw data, metrics, and metadata
   - Can be loaded for further analysis

2. **Summary Table** (printed to console)
   - Shows aggregate metrics across strategies
   - Includes mean ± std for key metrics

3. **Comparison Plots** (`evaluation/results_TIMESTAMP.png`, if matplotlib installed)
   - Visual comparison of strategies
   - 6 subplots showing different metrics

### Key Metrics Explained

#### Constraint/Correctness Metrics

- **Conflict-free %**: Percentage of schedules with no overlapping events (higher is better)
- **Deadline Compliance %**: Percentage of tasks meeting their deadlines (higher is better)
- **Parsing Success %**: Percentage of valid JSON outputs from LLM (higher is better)

#### Quality/Utility Metrics

- **Workload Variance**: Variance in daily hours (lower = better balanced)
- **Average Daily Hours**: Mean hours scheduled per day
- **Completion Ratio**: Fraction of requested hours that were scheduled
- **Fragmentation Score**: Average number of blocks per task (lower = less splitting)
- **Makespan (days)**: Time span from first to last scheduled event

#### System Metrics

- **API Cost ($)**: Total cost per test case (GPT-4o pricing)
- **Latency (seconds)**: Time to generate schedule
- **Total Tokens**: Prompt + completion tokens

### Interpreting Results

**Example Summary Table:**

```
Strategy             | Conflict-free % | Deadline %   | Parse %    | Workload Var | Cost ($)
----------------------------------------------------------------------------------------------------
Baseline             |          100.0% |  95.5± 8.2% |    100.0% |  4.23± 1.56 | 0.000±0.000
Zero Shot            |           93.3% |  92.1± 9.5% |     86.7% |  3.87± 2.10 | 0.112±0.023
Few Shot             |           96.7% |  94.8± 7.3% |     93.3% |  3.45± 1.82 | 0.125±0.028
Chain of Thought     |           90.0% |  91.5±10.2% |     83.3% |  4.01± 2.34 | 0.145±0.032
Constraint First     |           96.7% |  96.2± 6.8% |     90.0% |  3.28± 1.65 | 0.118±0.025
```

**Insights from this example:**
- Baseline has perfect conflict-free rate (deterministic algorithm)
- Few-shot and constraint-first strategies perform best among LLM approaches
- Chain-of-thought has higher cost due to longer outputs
- Constraint-first achieves best workload balance

---

## Customization

### Adding New Test Cases

Edit `evaluation/tests.json` and add new test case objects following this structure:

```json
{
  "id": 31,
  "split_type": "standard",
  "feasibility": "feasible",
  "preferences": {
    "study_windows": "9am-5pm",
    "max_daily_hours": 6,
    "break_pattern": "15 min every 2 hours",
    "additional_notes": "No weekends"
  },
  "existing_events": [
    {
      "id": "evt1",
      "summary": "Lecture",
      "start": {"dateTime": "2025-12-15T10:00:00", "timeZone": "America/New_York"},
      "end": {"dateTime": "2025-12-15T11:30:00", "timeZone": "America/New_York"},
      "description": "CS class"
    }
  ],
  "new_tasks": [
    {
      "id": 1,
      "name": "Problem Set",
      "subject": "Math",
      "estimated_hours": 4.0,
      "deadline": "2025-12-20",
      "priority": "high"
    }
  ]
}
```

### Modifying Prompting Strategies

Edit `evaluation/prompts.py` and modify the `build_prompts()` method of any strategy class.

For example, to adjust the zero-shot prompt:

```python
class ZeroShotStrategy(PromptStrategy):
    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
        Your modified system prompt here...
        """
        # ...
```

### Adding a New Prompting Strategy

1. Create a new class in `evaluation/prompts.py`:

```python
class MyCustomStrategy(PromptStrategy):
    def __init__(self):
        super().__init__(
            name="my_custom",
            description="My custom prompting approach"
        )

    def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = "..."
        user_prompt = f"..."
        return system_prompt, user_prompt
```

2. Add to the strategy registry:

```python
STRATEGIES = {
    'zero_shot': ZeroShotStrategy(),
    'few_shot': FewShotStrategy(),
    'chain_of_thought': ChainOfThoughtStrategy(),
    'constraint_first': ConstraintFirstStrategy(),
    'my_custom': MyCustomStrategy()  # Add your strategy
}
```

3. Run evaluation with your new strategy:

```bash
python evaluation/run_evaluation.py --strategies my_custom
```

### Adding Custom Metrics

Edit `evaluation/metrics.py` and add new metric functions. Then update `compute_all_metrics()` to include them.

---

## Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError

**Error:** `ModuleNotFoundError: No module named 'openai'`

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

#### 2. API Key Not Found

**Error:** `Error: OpenAI API key required`

**Solution:** Set your API key:
```bash
export OPENAI_API_KEY="sk-your-key"
```

#### 3. Rate Limit Errors

**Error:** `RateLimitError: Rate limit exceeded`

**Solution:** Add delays between API calls or reduce the number of test cases:
```bash
python evaluation/run_evaluation.py --num-cases 5
```

#### 4. JSON Parsing Failures

If you see many parsing failures, check:
- Model temperature (lower is more consistent)
- Prompt clarity (ensure JSON format is emphasized)
- Model capabilities (GPT-4o generally performs better than GPT-3.5)

#### 5. Import Errors from Backend

**Error:** `ModuleNotFoundError: No module named 'backend'`

**Solution:** Ensure you're running from the project root:
```bash
cd /Users/rahmaa/school/cs4701/llm-scheduler
python evaluation/run_evaluation.py
```

### Getting Help

If you encounter issues not covered here:

1. Check the console output for detailed error messages
2. Look at the generated results JSON file for clues
3. Try running with `--verbose` flag
4. Test with a single case: `--num-cases 1`

---

## Advanced Usage

### Programmatic Usage

You can also use the evaluator programmatically in Python:

```python
from evaluation.evaluator import Evaluator

# Initialize
evaluator = Evaluator(api_key="your-key", model="gpt-4o")

# Load test cases
test_cases = evaluator.load_test_cases()

# Run on a single test case
test_case = test_cases[0]

# Baseline
events, metrics = evaluator.run_baseline(test_case)
print(f"Baseline conflicts: {metrics.num_conflicts}")

# LLM with specific strategy
events, metrics = evaluator.run_llm_with_strategy(test_case, "few_shot")
print(f"LLM cost: ${metrics.api_cost:.4f}")

# Full evaluation
results = evaluator.evaluate_all(
    test_cases=test_cases[:10],  # First 10 cases
    strategies=["zero_shot", "few_shot"],
    output_file="my_results.json"
)
```

### Batch Processing

For large-scale evaluations, you can split the workload:

```bash
# Terminal 1 - Test cases 1-10
python evaluation/run_evaluation.py --num-cases 10 --output results_batch1.json

# Terminal 2 - Test cases 11-20
python evaluation/run_evaluation.py --num-cases 10 --output results_batch2.json
```

Then combine results manually or write a script to merge the JSON files.

### Statistical Analysis

For research papers, you may want to run statistical tests:

```python
from scipy import stats
import json

# Load results
with open('evaluation/results.json') as f:
    results = json.load(f)

# Extract metrics for two strategies
baseline_deadlines = [r['baseline']['deadline_compliance_rate'] for r in results['results']]
llm_deadlines = [r['llm_strategies']['few_shot']['deadline_compliance_rate'] for r in results['results']]

# Paired t-test
t_stat, p_value = stats.ttest_rel(baseline_deadlines, llm_deadlines)
print(f"t-statistic: {t_stat:.4f}, p-value: {p_value:.4f}")

# Wilcoxon signed-rank test (non-parametric alternative)
w_stat, p_value = stats.wilcoxon(baseline_deadlines, llm_deadlines)
print(f"Wilcoxon statistic: {w_stat:.4f}, p-value: {p_value:.4f}")
```

---

## Cost Estimation

Using GPT-4o with the default configuration:

- **Per test case:** ~$0.10 - $0.15
- **Full evaluation (30 cases × 4 strategies):** ~$12 - $18
- **Subset (10 cases × 2 strategies):** ~$2 - $3

Cost varies based on:
- Number of tasks per test case
- Number of existing events
- Complexity of prompts
- Model response length

---

## For Your Final Report

### Recommended Evaluation Setup

For a comprehensive evaluation in your final report:

1. **Run full evaluation:**
   ```bash
   python evaluation/run_evaluation.py --output final_results.json
   ```

2. **Generate LaTeX table:**
   ```python
   from evaluation.analysis import save_latex_table
   import json

   with open('evaluation/final_results.json') as f:
       results = json.load(f)

   save_latex_table(results, 'evaluation/results_table.tex')
   ```

3. **Include in report:**
   - Summary table (from console output or LaTeX)
   - Comparison plots (PNG file)
   - Discussion of which strategy performed best and why
   - Cost-quality tradeoff analysis
   - Statistical significance tests (if applicable)

### Suggested Report Sections

1. **Methodology:** Describe the 4 prompting strategies and baseline
2. **Experimental Setup:** 30 test cases, metrics used
3. **Results:** Present summary table and plots
4. **Analysis:** Discuss findings, compare strategies
5. **Discussion:** Insights on LLM reasoning, limitations, future work

---

## Quick Reference

### Most Common Commands

```bash
# Full evaluation (all 30 cases, all 4 strategies)
python evaluation/run_evaluation.py

# Quick test (5 cases, 2 strategies)
python evaluation/run_evaluation.py --num-cases 5 --strategies zero_shot few_shot

# Custom output
python evaluation/run_evaluation.py --output my_experiment.json

# Different model
python evaluation/run_evaluation.py --model gpt-4
```

### File Locations

- **Test cases:** `evaluation/tests.json`
- **Results:** `evaluation/results_*.json`
- **Plots:** `evaluation/results_*.png`
- **Code:** `evaluation/*.py`

---

## Contact and Support

For questions or issues related to this evaluation pipeline:

1. Check this documentation first
2. Review the code comments in each Python file
3. Consult the planning document: `planning/evaluation_plan.md`

Good luck with your evaluation and final report!
