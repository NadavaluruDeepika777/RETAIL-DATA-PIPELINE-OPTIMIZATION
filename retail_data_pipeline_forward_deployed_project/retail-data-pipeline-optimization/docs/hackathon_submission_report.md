# Retail Data Pipeline Optimization
## Hackathon Technical Submission Report

**Project type:** Local-first Data Engineering pipeline and analytical SQL optimization  
**Technology:** Python, Pandas, NumPy, DuckDB, SQL, Pytest  
**Data:** Deterministic synthetic retail records  
**Execution target:** Local machine or Google Colab

## 1. Executive Summary
This project implements a reproducible batch workflow for synthetic retail data. It generates related customer, product, order, and order-item tables; validates records; quarantines invalid rows with explicit rejection reasons; records run metadata; reconciles row counts; and benchmarks an analytical SQL workload.

The optimization compares a baseline query that joins and aggregates source tables for each report request with a precomputed category-level summary. The packaged benchmark records a 6.74x improvement in median summary-read latency versus the baseline query, while confirming that the baseline and optimized category results match. This measurement applies to reading an already-built summary, not to a single end-to-end run including summary construction.

## 2. Business Problem
Repeated analytical queries often scan, join, filter, and aggregate the same data. As the workload grows or the report is requested frequently, this repeated work can increase latency and resource use. A pipeline also needs to make invalid data visible, preserve traceability, and explain row-count differences instead of silently dropping records.

## 3. Objectives
- Define related source entities, keys, and business rules.
- Generate reproducible synthetic data with deliberate defects.
- Validate data quality and referential integrity.
- Quarantine rejected rows with source lineage and reasons.
- Record run status, timing, counts, and failure details.
- Reconcile input, valid, and rejected rows.
- Compare baseline and precomputed-summary SQL results.
- Measure query latency and document trade-offs.
- Provide tests and clean-environment setup instructions.

## 4. Architecture
The generator creates the four retail entities. The pipeline attaches `run_id`, `source_file`, and `source_row_number`, validates parent tables before child tables, separates valid and rejected records, checks row-count reconciliation, and writes CSV outputs and a JSON run report. A separate benchmark loads validated outputs into DuckDB, runs baseline SQL, builds a category summary, compares results, measures timings, and saves an execution plan.

See `docs/architecture.md` for the component flow and entity relationships.

## 5. Data Model and Business Rules
- `customers`: one row per `customer_id`.
- `products`: one row per `product_id`.
- `orders`: one row per `order_id`, referencing a customer.
- `order_items`: one row per `order_item_id`, referencing an order and a product.

Only `COMPLETED` orders contribute to revenue and units sold. Revenue is `SUM(quantity * unit_price)`. Completed orders are counted distinctly per product category. Required fields, keys, references, numeric ranges, dates, and status values are validated. `city` is intentionally nullable.

The complete field definitions and rejection reason codes are in `docs/data_dictionary.md`.

## 6. Data Quality and Observability
Every pipeline run creates a UUID `run_id`, UTC start/end timestamps, duration, status, per-table input/valid/rejected counts, rejection counts by reason, and an error field when the run fails. Rejected rows are written to `outputs/quarantine/` with traceability metadata. The pipeline requires `input_rows = valid_rows + rejected_rows` for every table before publishing outputs.

## 7. Recorded Execution Evidence
The packaged successful run recorded:

| Table | Input rows | Valid rows | Rejected rows |
|---|---:|---:|---:|
| customers | 1,001 | 1,000 | 1 |
| products | 100 | 100 | 0 |
| orders | 5,000 | 4,999 | 1 |
| order_items | 10,000 | 9,993 | 7 |
| **Total** | **16,101** | **16,092** | **9** |

All table-level row counts reconcile. Rejection examples include a missing customer name, an order referencing an invalid customer, order items referencing invalid order/product keys, and non-positive quantity/price values.

## 8. Optimization and Results
The baseline query joins order items, orders, and products, filters to completed orders, and aggregates by category. The optimized query reads a precomputed category summary. The benchmark checks result equivalence before reporting timing.

| Metric | Result |
|---|---:|
| Baseline median query time | 2.852 ms |
| Summary build time | 2.663 ms |
| Optimized summary-read median | 0.423 ms |
| Summary-read speedup | 6.74x |
| Summary-read runtime reduction | 85.16% |
| Build + one summary read | 3.087 ms |
| Correctness comparison | PASS |
| Timing repetitions | 7 |

The speedup excludes summary construction. For only one report request, build plus read is slightly slower than the baseline. Precomputation becomes useful when the summary is reused for multiple report requests before needing refresh.

The benchmark report and baseline execution plan are saved under `outputs/benchmarks/`.

## 9. Testing
The repository includes 20 tests across validation, pipeline, and optimization modules. The tests cover required fields, whitespace, duplicates, numeric constraints, dates, invalid references, empty frames/runs, reconciliation, reruns, benchmark artifacts, result correctness, invalid repetition settings, and SQL-file consistency.

Before final submission, execute `python -m pytest -q` in a clean virtual environment and preserve the complete terminal output as evidence. A test definition is not the same as a verified passing run.

## 10. Reproducibility
The project uses pinned dependencies in `requirements.txt`, a fixed default seed, and configurable synthetic row counts. It can run locally without credentials or external services. Full installation and execution commands are in `README.md` and `docs/runbook.md`.

## 11. Design Trade-offs and Limitations
- Data is synthetic and may not represent production distributions.
- The benchmark uses an in-memory DuckDB database and a workload of approximately 10,000 order items.
- External CSV/API ingestion and schema versioning are not implemented.
- Reruns replace current outputs, but multi-file publication is not transactionally atomic.
- Incremental processing, checkpoint/resume, late-arriving data, and backfill are not implemented.
- Precomputed summaries require a refresh strategy when source data changes.
- The recorded latency improvement must be re-measured on larger datasets and the evaluator's environment.

## 12. Future Improvements
1. Add external CSV ingestion with explicit schema-drift policy.
2. Publish all table outputs atomically using run-specific staging and a controlled commit/pointer.
3. Add larger benchmark runs and report environment details.
4. Add late-arriving-data, retry, and failure-injection tests.
5. Add CI to run tests on every commit.
6. Add summary refresh/freshness metadata and incremental processing if required.

## 13. Conclusion
The project demonstrates the core engineering loop requested by the problem statement: generate reproducible data, validate it, preserve rejected records, reconcile counts, test behavior, optimize a repeated analytical query, and report measurable results with limitations. It prioritizes correctness and evidence over unnecessary infrastructure.

## Submission checklist
- [ ] Run tests in a clean environment and save the full passing output.
- [ ] Run the pipeline and confirm a successful JSON report.
- [ ] Run the benchmark and confirm `correctness: PASS`.
- [ ] Review README and all documentation links.
- [ ] Remove machine-specific paths, secrets, and unnecessary duplicate files.
- [ ] Push the final source and documentation to GitHub.
- [ ] Add the exact final commit hash to the hackathon submission form.
