# LLM Scheduler Evaluation Pipeline

A comprehensive evaluation framework for comparing LLM-based scheduling strategies against a greedy baseline algorithm.

## Quick Start

```bash
# 1. Set your OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# 2. Run a quick test (1 test case)
python evaluation/run_evaluation.py --num-cases 1

# 3. Run full evaluation (30 test cases, 4 strategies)
python evaluation/run_evaluation.py
```

## What's Included

### Core Files

- **`tests.json`** (75KB) - 30 carefully designed test cases covering standard, edge, and realistic scheduling scenarios
- **`prompts.py`** - 4 prompting strategies: zero-shot, few-shot, chain-of-thought, constraint-first
- **`metrics.py`** - Comprehensive metrics: conflicts, deadlines, workload balance, cost, etc.
- **`evaluator.py`** - Main evaluation pipeline
- **`run_evaluation.py`** - Command-line interface
- **`analysis.py`** - Results visualization and LaTeX table generation
- **`instructions.md`** - Complete setup and usage guide (see this for detailed instructions)

### Helper Files

- **`test_pipeline.py`** - Test suite to verify installation
- **`prompts.md`** - Original prompt documentation (converted to prompts.py)

## Project Structure

```
evaluation/
├── tests.json                    # 30 test cases
├── prompts.py                    # 4 prompting strategies
├── metrics.py                    # Metrics computation
├── evaluator.py                  # Evaluation pipeline
├── run_evaluation.py             # Main CLI script
├── analysis.py                   # Visualization
├── test_pipeline.py              # Tests
├── instructions.md               # Full documentation
└── README.md                     # This file
```

## Test Cases (30 total)

The test suite includes:
- **Standard cases** (Mix of 3-10 tasks, varied deadlines)
- **Edge cases** (Tight deadlines, impossible constraints)
- **Realistic cases** (Student workload patterns)

Each test case includes:
- User preferences (study windows, max hours, break patterns)
- Existing calendar events (lectures, meetings)
- New tasks to schedule (with deadlines, priorities, estimated hours)
- Feasibility label

## Prompting Strategies (4)

1. **Zero-shot** - Direct prompting with clear instructions
2. **Few-shot** - Example input-output pairs before main task
3. **Chain-of-thought** - Step-by-step reasoning (internal)
4. **Constraint-first** - Explicit constraint enumeration

## Evaluation Metrics

### Constraint/Correctness
- **Conflict-free rate** - % of schedules with no overlaps
- **Deadline compliance** - % of tasks meeting deadlines
- **Parsing success** - % of valid JSON outputs

### Quality/Utility
- **Workload variance** - Balance across days (lower is better)
- **Completion ratio** - Fraction of hours scheduled
- **Fragmentation** - Average blocks per task
- **Makespan** - Time span of schedule

### System
- **API cost** - Total cost in USD
- **Latency** - Time to generate schedule
- **Token usage** - Prompt + completion tokens

## Usage Examples

```bash
# Run specific strategies only
python evaluation/run_evaluation.py --strategies zero_shot few_shot

# Run first 10 test cases
python evaluation/run_evaluation.py --num-cases 10

# Custom output file
python evaluation/run_evaluation.py --output my_results.json

# Different model
python evaluation/run_evaluation.py --model gpt-4

# Verbose output
python evaluation/run_evaluation.py --verbose

# Skip baseline (LLM-only)
python evaluation/run_evaluation.py --skip-baseline
```

## Expected Results Format

Running the evaluation produces:

1. **Console output** - Real-time progress and summary table
2. **JSON results file** - Complete data for all runs
3. **Comparison plots** (if matplotlib installed) - Visual comparison

Sample summary table:

```
Strategy             | Conflict-free % | Deadline %   | Parse %    | Workload Var | Cost ($)
----------------------------------------------------------------------------------------------------
Baseline             |          100.0% |  95.5± 8.2% |    100.0% |  4.23± 1.56 | 0.000±0.000
Zero Shot            |           93.3% |  92.1± 9.5% |     86.7% |  3.87± 2.10 | 0.112±0.023
Few Shot             |           96.7% |  94.8± 7.3% |     93.3% |  3.45± 1.82 | 0.125±0.028
Chain of Thought     |           90.0% |  91.5±10.2% |     83.3% |  4.01± 2.34 | 0.145±0.032
Constraint First     |           96.7% |  96.2± 6.8% |     90.0% |  3.28± 1.65 | 0.118±0.025
```

## Cost Estimate

- **Per test case:** ~$0.10 - $0.15
- **Full evaluation (30 × 4):** ~$12 - $18
- **Quick test (10 × 2):** ~$2 - $3

## Verification

Before running the full evaluation, verify everything works:

```bash
# Run the test suite
python evaluation/test_pipeline.py

# Expected output: "✓ All tests passed!"
```

## For Your Final Report

### Recommended Workflow

1. Run full evaluation:
   ```bash
   python evaluation/run_evaluation.py --output final_results.json
   ```

2. Generate LaTeX table (optional):
   ```python
   from evaluation.analysis import save_latex_table
   import json

   with open('evaluation/final_results.json') as f:
       results = json.load(f)

   save_latex_table(results)
   ```

3. Include in report:
   - Summary metrics table
   - Comparison plots
   - Statistical analysis (if applicable)
   - Discussion of findings

### Key Research Questions to Address

1. Which prompting strategy achieves the best constraint satisfaction?
2. Is there a cost-quality tradeoff among strategies?
3. How do LLM schedulers compare to the greedy baseline?
4. What types of test cases are most challenging for LLMs?
5. Do complex prompts (CoT) provide better reasoning than simpler ones?

## Customization

### Adding Test Cases

Edit `tests.json` following the existing structure. Each test case needs:
- `id`, `split_type`, `feasibility`
- `preferences` (study_windows, max_daily_hours, etc.)
- `existing_events` (Google Calendar format)
- `new_tasks` (with deadlines, priorities, estimated hours)

### Modifying Prompts

Edit the strategy classes in `prompts.py`. Each strategy implements:
```python
def build_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
    system_prompt = "..."
    user_prompt = "..."
    return system_prompt, user_prompt
```

### Adding Metrics

Add new metric functions to `metrics.py` and update `compute_all_metrics()`.

## Troubleshooting

**API key error?**
```bash
export OPENAI_API_KEY="sk-your-key"
```

**Import errors?**
```bash
pip install -r requirements.txt
```

**Rate limits?**
```bash
python evaluation/run_evaluation.py --num-cases 5
```

**See instructions.md for detailed troubleshooting.**

## Implementation Details

- **Language:** Python 3.9+
- **Dependencies:** openai, numpy, jsonschema, matplotlib (optional)
- **Baseline:** Greedy algorithm with priority weighting
- **LLM:** GPT-4o (configurable)
- **Test suite:** 30 cases, ~75KB JSON
- **Metrics:** 15+ quantitative measures

## Files Modified in Existing Codebase

No changes were made to the existing app code. All evaluation code is self-contained in the `evaluation/` directory and imports from the existing `backend/` modules.

## Next Steps

1. ✅ Install dependencies (`pip install -r requirements.txt`)
2. ✅ Set API key (`export OPENAI_API_KEY="..."`)
3. ✅ Run tests (`python evaluation/test_pipeline.py`)
4. 🔄 Quick evaluation (`python evaluation/run_evaluation.py --num-cases 1`)
5. 🔄 Full evaluation (`python evaluation/run_evaluation.py`)
6. 📊 Analyze results for your final report

## Questions?

Refer to `instructions.md` for comprehensive documentation including:
- Detailed installation steps
- All command-line options
- Advanced usage examples
- Statistical analysis guide
- Report writing suggestions

---

**Status:** ✅ Tested and verified - All pipeline tests passing

**Last updated:** December 12, 2025
