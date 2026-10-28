
from pathlib import Path
import json
import time
import statistics

import duckdb
import pandas as pd


# ---------------------------------------------------------
# 1. BASELINE ANALYTICAL QUERY
# ---------------------------------------------------------
# Calculates category-level revenue, units sold, and distinct
# completed orders by joining the original validated tables.

BASELINE_SQL = """
SELECT
    p.category,
    SUM(oi.quantity * oi.unit_price) AS revenue,
    SUM(oi.quantity) AS units_sold,
    COUNT(DISTINCT o.order_id) AS completed_orders
FROM clean_order_items AS oi
JOIN clean_orders AS o
    ON oi.order_id = o.order_id
JOIN clean_products AS p
    ON oi.product_id = p.product_id
WHERE o.status = 'COMPLETED'
GROUP BY p.category
ORDER BY p.category
"""


# ---------------------------------------------------------
# 2. BUILD PRECOMPUTED CATEGORY SUMMARY
# ---------------------------------------------------------
# This summary performs the expensive joins and aggregations
# once, rather than repeating them for every report request.

SUMMARY_BUILD_SQL = """
CREATE OR REPLACE TABLE category_sales_summary AS
SELECT
    p.category,
    SUM(oi.quantity * oi.unit_price) AS revenue,
    SUM(oi.quantity) AS units_sold,
    COUNT(DISTINCT o.order_id) AS completed_orders
FROM clean_order_items AS oi
JOIN clean_orders AS o
    ON oi.order_id = o.order_id
JOIN clean_products AS p
    ON oi.product_id = p.product_id
WHERE o.status = 'COMPLETED'
GROUP BY p.category
"""


# ---------------------------------------------------------
# 3. OPTIMIZED REPORT QUERY
# ---------------------------------------------------------
# Reads the precomputed summary rather than joining all
# source tables for every report request.

SUMMARY_READ_SQL = """
SELECT
    category,
    revenue,
    units_sold,
    completed_orders
FROM category_sales_summary
ORDER BY category
"""


# ---------------------------------------------------------
# 4. BENCHMARK A QUERY
# ---------------------------------------------------------

def benchmark_query(con, sql, repetitions=7):
    """
    Warm up a SQL query and measure its execution time.

    Returns median, minimum, maximum, and repetition count.
    Warm-up time is excluded from the measurements.
    """

    if (
        not isinstance(repetitions, int)
        or isinstance(repetitions, bool)
        or repetitions < 1
    ):
        raise ValueError(
            "repetitions must be a positive integer"
        )

    # Warm-up execution.
    con.execute(sql).fetchall()

    execution_times = []

    for _ in range(repetitions):
        start_time = time.perf_counter()

        con.execute(sql).fetchall()

        elapsed = time.perf_counter() - start_time
        execution_times.append(elapsed)

    return {
        "median_seconds": statistics.median(execution_times),
        "min_seconds": min(execution_times),
        "max_seconds": max(execution_times),
        "repetitions": repetitions,
    }


# ---------------------------------------------------------
# 5. RUN THE COMPLETE BENCHMARK
# ---------------------------------------------------------

def run_benchmark(
    validated_dir="outputs/validated",
    output_dir="outputs/benchmarks",
    repetitions=7,
):
    """
    Load validated CSVs into DuckDB, benchmark the baseline
    query against a precomputed summary, verify correctness,
    and save benchmark artifacts.

    Returns a dictionary containing benchmark results.
    """

    # Validate settings before checking input files.
    if (
        not isinstance(repetitions, int)
        or isinstance(repetitions, bool)
    ):
        raise ValueError(
            "repetitions must be a positive integer"
        )

    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least 1"
        )

    validated_dir = Path(validated_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(":memory:")

    try:
        # -------------------------------------------------
        # Load validated CSV files into DuckDB.
        # -------------------------------------------------

        tables = [
            "customers",
            "products",
            "orders",
            "order_items",
        ]

        for name in tables:
            csv_path = validated_dir / f"{name}.csv"

            if not csv_path.exists():
                raise FileNotFoundError(
                    f"Validated input not found: {csv_path}"
                )

            df = pd.read_csv(csv_path)

            # Remove pipeline metadata; it is not part of
            # the analytical business schema.
            metadata_columns = [
                "source_file",
                "source_row_number",
                "run_id",
            ]

            df = df.drop(
                columns=[
                    column
                    for column in metadata_columns
                    if column in df.columns
                ]
            )

            con.register("input_df", df)

            con.execute(
                f"""
                CREATE OR REPLACE TABLE clean_{name}
                AS SELECT * FROM input_df
                """
            )

            con.unregister("input_df")

        # -------------------------------------------------
        # Run the baseline query.
        # -------------------------------------------------

        baseline_result = con.execute(
            BASELINE_SQL
        ).fetchdf()

        baseline_result = baseline_result.sort_values(
            "category"
        ).reset_index(drop=True)

        baseline_csv = (
            output_dir / "category_sales_baseline.csv"
        )

        baseline_result.to_csv(
            baseline_csv,
            index=False,
        )

        baseline_metrics = benchmark_query(
            con,
            BASELINE_SQL,
            repetitions=repetitions,
        )

        # -------------------------------------------------
        # Capture the baseline execution plan.
        # -------------------------------------------------

        plan_rows = con.execute(
            "EXPLAIN ANALYZE " + BASELINE_SQL
        ).fetchall()

        plan_text = "\n".join(
            str(row[-1]) for row in plan_rows
        )

        plan_path = (
            output_dir / "baseline_query_plan.txt"
        )

        plan_path.write_text(
            plan_text,
            encoding="utf-8",
        )

        # -------------------------------------------------
        # Build the precomputed category summary.
        # -------------------------------------------------

        summary_build_start = time.perf_counter()

        con.execute(SUMMARY_BUILD_SQL)

        summary_build_seconds = (
            time.perf_counter() - summary_build_start
        )

        # -------------------------------------------------
        # Read and benchmark the optimized summary.
        # -------------------------------------------------

        summary_result = con.execute(
            SUMMARY_READ_SQL
        ).fetchdf()

        summary_result = summary_result.sort_values(
            "category"
        ).reset_index(drop=True)

        summary_csv = (
            output_dir / "category_sales_summary.csv"
        )

        summary_result.to_csv(
            summary_csv,
            index=False,
        )

        summary_metrics = benchmark_query(
            con,
            SUMMARY_READ_SQL,
            repetitions=repetitions,
        )

        # -------------------------------------------------
        # Verify result correctness.
        # -------------------------------------------------

        try:
            pd.testing.assert_frame_equal(
                baseline_result,
                summary_result,
                check_dtype=False,
                check_exact=False,
                rtol=1e-9,
                atol=1e-9,
            )

            correctness = "PASS"

        except AssertionError as error:
            raise AssertionError(
                "Baseline and optimized query results differ"
            ) from error

        # -------------------------------------------------
        # Calculate performance improvements.
        # -------------------------------------------------

        baseline_seconds = baseline_metrics[
            "median_seconds"
        ]

        summary_seconds = summary_metrics[
            "median_seconds"
        ]

        speedup = (
            baseline_seconds / summary_seconds
            if summary_seconds > 0
            else None
        )

        runtime_reduction_pct = (
            (baseline_seconds - summary_seconds)
            / baseline_seconds
            * 100
            if baseline_seconds > 0
            else None
        )

        # Include summary build time to make the trade-off
        # visible. Summary-read speedup excludes build time.
        amortized_first_use_seconds = (
            summary_build_seconds + summary_seconds
        )

        report = {
            "status": "SUCCESS",
            "correctness": correctness,
            "input_directory": str(validated_dir),
            "repetitions": repetitions,
            "baseline": baseline_metrics,
            "summary_build_seconds": summary_build_seconds,
            "optimized_summary_read": summary_metrics,
            "speedup": speedup,
            "runtime_reduction_pct": runtime_reduction_pct,
            "summary_build_plus_one_read_seconds": (
                amortized_first_use_seconds
            ),
            "category_count": int(
                len(baseline_result)
            ),
            "notes": [
                (
                    "Query timings exclude data loading and "
                    "the warm-up execution."
                ),
                (
                    "Speedup compares baseline query execution "
                    "with summary-read execution."
                ),
                (
                    "Summary build time is reported separately; "
                    "it is not included in the summary-read "
                    "speedup calculation."
                ),
                (
                    "Actual performance depends on data size, "
                    "hardware, caching, and workload."
                ),
            ],
        }

        # -------------------------------------------------
        # Save benchmark report.
        # -------------------------------------------------

        report_path = (
            output_dir / "benchmark_report.json"
        )

        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        return report

    finally:
        con.close()
