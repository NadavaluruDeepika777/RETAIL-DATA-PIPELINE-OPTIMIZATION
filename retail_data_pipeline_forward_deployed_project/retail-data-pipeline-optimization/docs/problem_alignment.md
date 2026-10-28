# Problem Statement Alignment Matrix

This matrix distinguishes implemented capabilities from partial or future scope. It is intended to help reviewers assess the project without overstating functionality.

| Problem-statement requirement | Project evidence | Status / qualification |
|---|---|---|
| Define schemas, data types, keys, relationships | `docs/data_dictionary.md`, generator and validation modules | Implemented for synthetic retail entities |
| Reproducible sample and scalable generator | `src/retail_pipeline/generator.py`, fixed seed and configurable counts | Implemented; larger performance runs still need evidence |
| Ingestion, validation, transformation, publishing | `pipeline.py` generates data, validates, and publishes CSV outputs | Partial: data is generated internally; external CSV/API ingestion is not implemented |
| Rerun safety and run metrics | Per-run UUID JSON report; output replacement; counts and errors | Partial: repeat-run replacement works, but multi-file publishing is not atomic |
| Automated tests and sample queries | `tests/`, `sql/`, benchmark outputs | Implemented test definitions; record a fresh full-suite pass as evidence |
| Primary keys and referential integrity | Validation functions and foreign-key checks | Implemented for defined entities |
| Traceable rejected records | Quarantine CSVs, source metadata, rejection reasons | Implemented |
| Preserve event/change history | Run reports retained; current tables replaced | Partial: no source-event history or SCD implementation |
| Malformed input and schema change | Validation handles malformed field values in generated frames | Partial: malformed external files and schema drift are not end-to-end implemented |
| Empty batch | Validation/pipeline tests and failed-run behavior | Covered at DataFrame/pipeline level; no external empty-file ingestion |
| Partial failure and retry | Error reporting and temporary files | Partial: no transactional multi-file commit or restart-from-checkpoint |
| Late/out-of-order data and backfill | Not implemented | Future work; not applicable to current generated batch flow |
| Idempotent rerun | Current outputs replaced rather than appended | Implemented for current generated-output semantics; not incremental upsert |
| Correctness reconciliation | Per-table row reconciliation and baseline/optimized result comparison | Implemented |
| Performance baseline and measurable improvement | `outputs/benchmarks/benchmark_report.json` and query plan | Implemented for default local workload; larger scale evidence recommended |
| Setup on a clean machine | `requirements.txt`, README, runbook | Documented; verify from a fresh environment before submission |
| Cloud deployment | Not required by the selected local-first design | Not implemented; local execution is the target |

## Honest submission statement

This is a local-first, reproducible batch data engineering demonstration. It implements synthetic data generation, validation, quarantine, lineage metadata, row-count reconciliation, per-run observability, and a DuckDB analytical query optimization benchmark. It demonstrates a measured improvement for reading a precomputed summary while checking output correctness. It does not claim production-grade transactional publishing, external ingestion, streaming, incremental backfill, or cloud deployment.
