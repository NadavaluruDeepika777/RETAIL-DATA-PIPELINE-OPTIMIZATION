# Performance Benchmark Report

## Benchmark question
Can repeated category-level retail reporting avoid re-running the same joins and aggregations for every report request by reading a precomputed summary instead?

## Method
1. Load validated CSV tables into an in-memory DuckDB database.
2. Run the baseline SQL query that joins order items, orders, and products, filters completed orders, and aggregates by category.
3. Build a category-level summary table.
4. Compare baseline and optimized result sets for correctness.
5. Warm up and time each query over seven repetitions.
6. Report median, minimum, maximum, summary-build time, and the baseline query plan.

## Recorded result

| Metric | Recorded value |
|---|---:|
| Baseline query median | 0.002852385 seconds (2.852 ms) |
| Baseline query minimum | 2.604 ms |
| Baseline query maximum | 3.471 ms |
| Summary build time | 2.663 ms |
| Optimized summary-read median | 0.000423402 seconds (0.423 ms) |
| Optimized summary-read minimum | 0.369 ms |
| Optimized summary-read maximum | 0.512 ms |
| Summary-read speedup vs baseline | 6.74x |
| Summary-read runtime reduction | 85.16% |
| Build summary + one read | 3.087 ms |
| Categories in result | 4 |
| Correctness comparison | PASS |
| Repetitions | 7 |

Source: `outputs/benchmarks/benchmark_report.json`.

## Interpretation
The recorded summary-read median is about 6.74 times faster than running the baseline query, an 85.16% reduction in query-read time for this workload. This is not an end-to-end 6.74x improvement for a single report: building the summary takes 2.663 ms, so summary build plus one read takes approximately 3.087 ms, slightly longer than the baseline median of 2.852 ms.

Pre-aggregation is most beneficial when the same summary is queried repeatedly while source data remains unchanged. Summary refresh cost and freshness requirements must be included in a production design.

## Limitations
- The recorded workload is around 10,000 order items.
- The database is in-memory DuckDB.
- Timings exclude CSV loading and warm-up.
- Results depend on machine, software version, caching, and workload.
- No claim is made that this speedup generalizes to millions of records without further tests.

## Recommended follow-up experiment
Repeat the benchmark for 10,000, 100,000, and (where practical) 1,000,000 order items. Record machine details, seed, row counts, all timing repetitions, summary build time, and correctness status. Compare query-only latency and amortized cost across multiple report reads.
