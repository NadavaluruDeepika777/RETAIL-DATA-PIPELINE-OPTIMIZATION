# Test Plan and Acceptance Evidence

## Test execution

Run from the repository root after installing dependencies:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The repository defines 20 tests across `tests/test_validation.py`, `tests/test_pipeline.py`, and `tests/test_optimization.py`. Do not report all tests as passing until the command above completes successfully in the target environment. Save the terminal output as submission evidence.

## Test coverage matrix

| Scenario | Expected behavior | Test area |
|---|---|---|
| Valid records | Records pass validation | Validation |
| Empty input frame | Empty valid/rejected results are handled | Validation |
| Missing required field | Record rejected with explicit reason | Validation |
| Whitespace-only required text | Treated as missing | Validation |
| Non-numeric price/quantity | Record rejected | Validation |
| Zero or negative price/quantity | Record rejected | Validation |
| Fractional quantity | Record rejected as non-integer | Validation |
| Invalid ISO-style date | Record rejected | Validation |
| Duplicate primary key | Later field-clean duplicate rejected | Validation |
| Invalid customer reference | Order rejected | Pipeline |
| Invalid order/product reference | Order item rejected | Pipeline |
| Child references rejected parent | Child rejected | Pipeline |
| Input/valid/rejected reconciliation | Counts must balance per table | Pipeline |
| Rerun same generated workload | Current outputs are replaced, not appended | Pipeline |
| Baseline versus optimized result | Results must match within configured tolerance | Optimization |
| Benchmark artifacts | Report, result CSVs, and query plan are produced | Optimization |
| Invalid benchmark repetitions | Invalid parameter is rejected | Optimization |
| SQL source consistency | Benchmark SQL matches reviewed SQL files | Optimization |

## Required evidence to attach or preserve

- Full `pytest` terminal output.
- A successful JSON run report from `outputs/reports/`.
- Validated and quarantine row counts.
- `outputs/benchmarks/benchmark_report.json`.
- Baseline and optimized category result CSVs.
- `outputs/benchmarks/baseline_query_plan.txt`.

## Known coverage gaps / future tests

The current project does not yet implement external CSV/API ingestion, so malformed source-file parsing and formal schema drift are not end-to-end tested. It also does not provide transactional multi-file publication, so crash recovery during publication is a known limitation. Late-arriving data, incremental backfill, and persistent checkpoint/resume behavior are not implemented. These scenarios should be added if the scope expands.
