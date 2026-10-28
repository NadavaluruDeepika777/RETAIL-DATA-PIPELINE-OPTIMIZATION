# Design Decisions and Trade-offs

## 1. Local-first stack
**Decision:** Use Python, Pandas, NumPy, DuckDB, SQL, and Pytest.

**Reason:** This is a small, reproducible vertical slice that can run on a laptop or in Google Colab without credentials or managed services. DuckDB is suitable for demonstrating analytical SQL and pre-aggregation locally.

**Trade-off:** The current benchmark is in-memory and is not evidence of distributed or cloud-scale performance.

## 2. Synthetic data with a fixed seed
**Decision:** Generate retail entities with deterministic IDs and a configurable seed, and optionally inject known defects.

**Reason:** Reviewers can recreate test conditions without licensing, privacy, or network dependencies. Injected defects make rejection behavior visible.

**Trade-off:** Synthetic distributions do not fully represent real retail behavior. Results should not be generalized to production without representative data.

## 3. Validate parents before children
**Decision:** Validate customers/products before orders/order items and build foreign-key checks from accepted parent keys.

**Reason:** A child row must not pass if its parent is missing or rejected. This also makes rejection reasons understandable.

**Trade-off:** The current implementation validates in-memory DataFrames and is designed for the current batch size, not streaming or distributed processing.

## 4. Quarantine rather than silently discard
**Decision:** Preserve rejected rows with source metadata and `rejection_reasons`.

**Reason:** Operators can investigate and correct source defects; the pipeline's row counts remain reconcilable.

**Trade-off:** Quarantine retention, access control, and lifecycle policies would need to be added in a production system.

## 5. Reconcile before publication
**Decision:** Check `input_rows = valid_rows + rejected_rows` for every table before publishing output files.

**Reason:** A run should not publish if row accounting is inconsistent.

**Trade-off:** Each output file is renamed individually. A process crash between file replacements can leave files from different runs. Run-specific staging plus a single publication pointer or transactional storage is a future improvement.

## 6. Precompute repeated category aggregates
**Decision:** Compare a baseline query that joins and aggregates the source tables on each request with a query that reads a precomputed category summary.

**Reason:** When the same aggregate is requested repeatedly and source data has not changed, precomputation can reduce repeated query work.

**Trade-off:** Summary creation and refresh have a cost. For one report request, building the summary and reading it once can be slower than the baseline. The reported speedup compares summary-read latency only against baseline query latency.

## 7. Correctness before speed
**Decision:** Compare baseline and optimized result sets before treating the benchmark as successful.

**Reason:** An optimization is only acceptable if it preserves business results.

**Trade-off:** Floating-point comparisons use a small tolerance; currency-focused production pipelines should consider decimal arithmetic and an explicit rounding policy.

## 8. Reruns and idempotency
**Decision:** A rerun replaces the current validated and quarantine CSV outputs and writes a new run report with a new run ID.

**Reason:** It avoids appending the same generated batch to the current output files.

**Trade-off:** This is repeatable replacement, not full transactional idempotency or incremental upsert semantics. The current project does not implement checkpoints, restart-from-stage, backfill, or late-arriving-data logic.

## 9. Performance measurement
**Decision:** Warm up each query, repeat timing, report median/minimum/maximum, and report summary build time separately.

**Reason:** Repeated measurements and medians reduce the influence of a single noisy observation.

**Trade-off:** The workload contains about 10,000 order items and timing is in milliseconds. Hardware, cache state, and runtime conditions affect results. Larger-scale tests are required before drawing scalability conclusions.
