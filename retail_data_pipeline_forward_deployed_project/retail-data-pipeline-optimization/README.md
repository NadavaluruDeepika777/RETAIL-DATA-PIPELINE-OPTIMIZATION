# Retail Data Pipeline Optimization

## Documentation for Reviewers

- [`docs/hackathon_submission_report.md`](docs/hackathon_submission_report.md) — submission-ready technical report.
- [`docs/architecture.md`](docs/architecture.md) — architecture, entities, grain, and data flow.
- [`docs/data_dictionary.md`](docs/data_dictionary.md) — schema, keys, rules, and rejection codes.
- [`docs/design_decisions.md`](docs/design_decisions.md) — design rationale and trade-offs.
- [`docs/test_plan_and_acceptance.md`](docs/test_plan_and_acceptance.md) — test matrix and acceptance evidence.
- [`docs/problem_alignment.md`](docs/problem_alignment.md) — requirement-by-requirement implementation status.
- [`docs/benchmark_report.md`](docs/benchmark_report.md) — measured optimization results and caveats.
- [`docs/runbook.md`](docs/runbook.md) — clean setup, execution, output inspection, and troubleshooting.

## 1. Business Problem

Retail analytics teams often run reports that repeatedly scan source tables,
join data, filter records, and aggregate metrics. These operations can become
expensive as datasets grow.

This project builds a reproducible data engineering workflow that:

- Generates synthetic retail data.
- Validates records against data quality rules.
- Separates valid records from rejected records.
- Tracks pipeline runs and row counts.
- Benchmarks a baseline analytical SQL query.
- Builds a precomputed category-level summary.
- Compares query results to verify correctness.
- Measures query execution time and reports performance trade-offs.
- Uses automated tests to check pipeline behavior.

## 2. Project Objectives

1. Detect invalid and duplicate records.
2. Preserve rejected records with explanations.
3. Reconcile input, valid, and rejected row counts.
4. Make repeated pipeline executions reproducible.
5. Compare baseline and optimized analytical results.
6. Record benchmark metrics and execution plans.
7. Support execution on another computer using documented dependencies.

## 3. Architecture

```text
Synthetic Retail Data
        |
        v
Data Generation
        |
        v
Lineage Metadata
(source file, source row, run ID)
        |
        v
Data Validation
        |
        +--------------------+
        |                    |
        v                    v
Validated Records      Quarantined Records
        |                    |
        v                    v
Validated CSVs         Rejection Reasons
        |
        v
Load CSVs into DuckDB
        |
        v
Baseline SQL Query
        |
        v
Build Category Summary
        |
        v
Optimized Summary Query
        |
        v
Correctness Comparison
        |
        v
Benchmark Report and Query Plan
```

The pipeline and benchmark are separate stages. The pipeline generates
and validates records; the benchmark reads the validated CSV files and
loads the business tables into an in-memory DuckDB database.

## 4. Technology Stack

- Python
- Pandas
- NumPy
- DuckDB
- SQL
- Pytest
- Google Colab for development

## 5. Data Model

| Table | Purpose | Primary Key |
|---|---|---|
| customers | Customer details and signup dates | customer_id |
| products | Product details, categories, and prices | product_id |
| orders | Customer orders, dates, and statuses | order_id |
| order_items | Products and quantities within orders | order_item_id |

Relationships:

- Each order references a customer.
- Each order item references an order.
- Each order item references a product.

See `docs/data_dictionary.md` for column definitions and validation rules.

## 6. Data Quality Rules

The validation stage checks:

- Required values are present. Null and whitespace-only text both count as missing.
- Numeric fields (`unit_price`, `quantity`) are numeric. Non-numeric text is rejected as `must_be_numeric`.
- Quantity and price values are positive; quantity is a whole number.
- Dates (`signup_date`, `order_date`) parse as ISO-8601.
- Primary keys are unique. The first field-clean occurrence of a key is kept;
  later duplicates are rejected. An invalid first copy does not cause a valid
  later copy to be lost.
- Foreign keys reference records that passed validation in their parent table,
  so a child of a rejected parent is also rejected.
- Order status belongs to the allowed set:
  `COMPLETED`, `CANCELLED`, or `PENDING` (case-sensitive).
- `city` is nullable by design; it is not part of the required-field rules.
- Rejected records include every failed rule in `rejection_reasons`.

Each run report records, per table, the input, valid, and rejected row counts,
plus `rejections_by_reason` (how many times each rule fired).

Reconciliation runs for all tables before any output file is published. If it
fails, no validated or quarantine file is overwritten and the run is marked `FAILED`.

Each table's input rows must reconcile:

`input_rows = valid_rows + rejected_rows`

## 7. Analytical Metric Definitions

- **Revenue:** sum of quantity multiplied by unit price for completed orders.
- **Units sold:** sum of item quantities for completed orders.
- **Completed orders:** distinct completed order IDs represented in each category.

Cancelled and pending orders are excluded from these metrics.

## 8. Query Optimization Approach

### Baseline

The baseline query joins order items, orders, and products, then aggregates
the results by category each time the report runs.

### Optimized approach

The project precomputes a category-level summary and reads that summary for
subsequent reports.

The summary stores:

- Category
- Revenue
- Units sold
- Distinct completed orders

### Correctness first

The benchmark compares the baseline and optimized result sets. The benchmark
is considered successful only when those results match within a small
floating-point tolerance.

### Performance measurement

The benchmark:

1. Warms up each query.
2. Measures repeated executions.
3. Reports median, minimum, and maximum execution time.
4. Measures summary build time separately.
5. Calculates summary-read speedup and runtime reduction.
6. Saves the baseline query execution plan.

The reported summary-read speedup excludes summary build time. Therefore,
it should not be interpreted as the end-to-end speedup for a single report.
Performance also depends on dataset size, hardware, caching, and workload.

## 9. Repository Structure

```text
retail-data-pipeline-optimization/
├── src/
│   └── retail_pipeline/
│       ├── __init__.py
│       ├── generator.py
│       ├── validation.py
│       ├── pipeline.py
│       └── optimization.py
├── sql/
│   ├── baseline.sql
│   ├── build_category_summary.sql
│   └── optimized.sql
├── tests/
│   ├── test_validation.py
│   ├── test_pipeline.py
│   └── test_optimization.py
├── docs/
│   └── data_dictionary.md
├── outputs/
├── data/
├── requirements.txt
├── README.md
└── .gitignore
```

Generated output files may appear under `outputs/` when the project runs.

## 10. Setup on Another Computer

Install Python 3.11 or a compatible version supported by the pinned dependencies.

### Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

From the repository root:

```bash
python -m pip install -r requirements.txt
```

### Run automated tests

```bash
python -m pytest -q
```

### Run the pipeline

**Windows PowerShell**

```powershell
$env:PYTHONPATH = "src"
python -c "from retail_pipeline.pipeline import run_pipeline; print(run_pipeline())"
```

**macOS / Linux**

```bash
PYTHONPATH=src python -c "from retail_pipeline.pipeline import run_pipeline; print(run_pipeline())"
```

### Run the benchmark

**Windows PowerShell**

```powershell
$env:PYTHONPATH = "src"
python -c "from retail_pipeline.optimization import run_benchmark; print(run_benchmark())"
```

**macOS / Linux**

```bash
PYTHONPATH=src python -c "from retail_pipeline.optimization import run_benchmark; print(run_benchmark())"
```

Run the pipeline before the benchmark because the benchmark reads its
validated CSV outputs.

## 11. Expected Outputs

The pipeline writes validated records, quarantined records, and a JSON
report for each run.

The benchmark writes:

- `benchmark_report.json`
- `category_sales_baseline.csv`
- `category_sales_summary.csv`
- `baseline_query_plan.txt`

These outputs allow reviewers to inspect data quality, query results,
and measured performance.

## 12. Testing

Automated tests (20) cover:

- Duplicate primary keys, including an invalid first copy followed by a valid one.
- Missing and whitespace-only required values.
- Invalid foreign keys.
- Non-numeric, zero, negative, and fractional quantities or prices.
- Invalid dates.
- Empty input frames, and empty or undersized pipeline runs (reported as `FAILED`).
- Pipeline output and row reconciliation, including rejection-reason counts.
- Repeat-run behavior.
- Benchmark artifacts and baseline-versus-summary correctness.
- Invalid benchmark repetition counts.
- Inline benchmark SQL matching the reviewable `sql/*.sql` files.

Run the suite with:

```bash
python -m pytest -q
```

## 13. Limitations and Future Improvements

- Data is synthetic; production data distributions may behave differently.
- The benchmark uses an in-memory DuckDB database.
- The precomputed summary must be refreshed when source data changes.
- Small datasets may not benefit from pre-aggregation.
- Current rerun behavior replaces current validated and quarantine CSVs;
  it is not a transactional, multi-file production deployment. A crash
  between two file replacements can leave the validated and quarantine
  files from different runs. Each run report is kept separately.
- Input is generated, not ingested. There is no CSV/API ingestion, schema-version
  check beyond required columns, late-arriving-data handling, or backfill.
- The benchmark runs on about 10k order items, where timings are in
  milliseconds and noisy. Speedup figures are indicative only.
- Future work could add external CSV ingestion, incremental processing,
  schema-version management, larger workload tests, and CI automation.

## 14. Engineering Principle

Optimization must be measured, and correctness must be preserved.

A faster query is useful only when it returns the right result and the
cost of building and maintaining its summary is understood.
