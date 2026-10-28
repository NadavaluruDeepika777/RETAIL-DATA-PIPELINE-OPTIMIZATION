import sys
import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from retail_pipeline.pipeline import run_pipeline
from retail_pipeline.optimization import run_benchmark


def test_benchmark_creates_report_and_output_files(tmp_path):
    """Check that benchmarking creates all expected artifacts."""

    validated_dir = tmp_path / "validated"
    benchmark_dir = tmp_path / "benchmarks"

    # Create a small dataset for the benchmark.
    run_pipeline(
        output_dir=str(tmp_path / "pipeline_output"),
        seed=42,
        n_customers=100,
        n_products=20,
        n_orders=300,
        n_order_items=600,
    )

    # Use the pipeline's validated CSV files as benchmark inputs.
    validated_dir.mkdir(parents=True, exist_ok=True)

    source_dir = tmp_path / "pipeline_output" / "validated"

    for table_name in [
        "customers",
        "products",
        "orders",
        "order_items",
    ]:
        source_file = source_dir / f"{table_name}.csv"
        destination_file = validated_dir / f"{table_name}.csv"

        destination_file.write_bytes(source_file.read_bytes())

    result = run_benchmark(
        validated_dir=str(validated_dir),
        output_dir=str(benchmark_dir),
        repetitions=3,
    )

    assert result["status"] == "SUCCESS"
    assert result["correctness"] == "PASS"

    # Verify the benchmark report exists and is valid JSON.
    report_file = benchmark_dir / "benchmark_report.json"
    assert report_file.exists()

    report = json.loads(report_file.read_text())
    assert report["status"] == "SUCCESS"
    assert report["correctness"] == "PASS"

    # Verify expected result files were created.
    expected_files = [
        "category_sales_baseline.csv",
        "category_sales_summary.csv",
        "baseline_query_plan.txt",
    ]

    for filename in expected_files:
        assert (benchmark_dir / filename).exists()

    # Verify baseline and summary results match.
    baseline = pd.read_csv(
        benchmark_dir / "category_sales_baseline.csv"
    )
    summary = pd.read_csv(
        benchmark_dir / "category_sales_summary.csv"
    )

    pd.testing.assert_frame_equal(
        baseline,
        summary,
        check_dtype=False,
        check_exact=False,
        rtol=1e-9,
        atol=1e-9,
    )


def test_benchmark_rejects_zero_repetitions(tmp_path):
    """Benchmarking should not accept zero repetitions."""

    with pytest.raises((ValueError, RuntimeError)):
        run_benchmark(
            validated_dir=str(tmp_path / "missing_validated"),
            output_dir=str(tmp_path / "benchmarks"),
            repetitions=0,
        )


def _strip_sql(text):
    """Drop comment lines and trailing semicolons; normalise whitespace."""
    lines = [
        line for line in text.splitlines()
        if not line.strip().startswith("--")
    ]
    return " ".join(" ".join(lines).replace(";", " ").split())


def test_inline_sql_matches_sql_files():
    """Inline benchmark SQL must not drift from the reviewable sql/ files."""
    from retail_pipeline import optimization

    sql_dir = PROJECT_ROOT / "sql"

    assert _strip_sql(optimization.BASELINE_SQL) == _strip_sql(
        (sql_dir / "baseline.sql").read_text()
    )
    assert _strip_sql(optimization.SUMMARY_BUILD_SQL) == _strip_sql(
        (sql_dir / "build_category_summary.sql").read_text()
    )
    assert _strip_sql(optimization.SUMMARY_READ_SQL) == _strip_sql(
        (sql_dir / "optimized.sql").read_text()
    )
