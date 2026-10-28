# Runbook: Setup, Execute, Verify, Troubleshoot

## Requirements
- Python 3.11, 3.12, or 3.13 (the project metadata supports Python >=3.11 and <3.14).
- Terminal access.
- No API key, cloud account, or external database is required.

## 1. Get the project
Download or clone the repository and change to its root directory:

```bash
cd retail-data-pipeline-optimization
```

## 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Run automated tests

```bash
python -m pytest -q
```

A successful run should end with all collected tests passing. If the test runner reports a missing dependency, confirm the virtual environment is activated and reinstall `requirements.txt`.

## 5. Run the pipeline

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -c "from retail_pipeline.pipeline import run_pipeline; print(run_pipeline())"
```

macOS/Linux:

```bash
PYTHONPATH=src python -c "from retail_pipeline.pipeline import run_pipeline; print(run_pipeline())"
```

The default workload uses 1,000 customers, 100 products, 5,000 orders, and 10,000 order items, with deliberate invalid records enabled.

## 6. Run the benchmark

Run this only after a successful pipeline run.

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -c "from retail_pipeline.optimization import run_benchmark; print(run_benchmark())"
```

macOS/Linux:

```bash
PYTHONPATH=src python -c "from retail_pipeline.optimization import run_benchmark; print(run_benchmark())"
```

## 7. Inspect results

- `outputs/validated/`: records that passed validation.
- `outputs/quarantine/`: rejected records and reasons.
- `outputs/reports/run_<run_id>.json`: status, timestamps, duration, counts, rejection reason totals, and failure details.
- `outputs/benchmarks/benchmark_report.json`: correctness and timing results.
- `outputs/benchmarks/category_sales_baseline.csv`: baseline aggregate.
- `outputs/benchmarks/category_sales_summary.csv`: precomputed-summary result.
- `outputs/benchmarks/baseline_query_plan.txt`: baseline execution plan.

## 8. Scale the generated workload

The pipeline function accepts configurable counts:

```python
from retail_pipeline.pipeline import run_pipeline

result = run_pipeline(
    output_dir="outputs",
    seed=42,
    n_customers=10000,
    n_products=1000,
    n_orders=50000,
    n_order_items=100000,
)
print(result)
```

Use the same seed and workload settings when comparing repeated runs. The current benchmark has been recorded for the packaged default-sized dataset; larger benchmark results should be measured and saved separately.

## Troubleshooting

- **`ModuleNotFoundError: retail_pipeline`**: run from the repository root and set `PYTHONPATH=src` (or `$env:PYTHONPATH = "src"` in PowerShell).
- **DuckDB import error**: activate the virtual environment and run `python -m pip install -r requirements.txt`.
- **Benchmark fails because validated CSVs are missing**: run the pipeline first.
- **Pipeline reports `FAILED`**: open the referenced JSON run report and inspect its `error` field.
- **Outputs look stale**: check the latest run ID and timestamp. Each run creates a new report but replaces the current validated/quarantine CSVs.
