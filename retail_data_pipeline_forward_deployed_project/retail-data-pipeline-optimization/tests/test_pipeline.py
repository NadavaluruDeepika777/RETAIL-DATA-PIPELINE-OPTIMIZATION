
import sys
import json
from pathlib import Path

import pandas as pd
import pytest

# Make the src directory available for imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from retail_pipeline.pipeline import run_pipeline


def test_pipeline_success_and_reconciliation(tmp_path):
    """Check pipeline success, row counts, output files, and run report."""

    output_dir = tmp_path / "run_output"

    result = run_pipeline(
        output_dir=str(output_dir),
        seed=42,
        n_customers=100,
        n_products=20,
        n_orders=300,
        n_order_items=600,
    )

    # The pipeline should complete successfully.
    assert result["status"] == "SUCCESS"
    assert len(result["tables"]) == 4

    for table_name, counts in result["tables"].items():

        # Every input row must be valid or rejected.
        assert counts["input_rows"] == (
            counts["valid_rows"] + counts["rejected_rows"]
        )

        valid_file = (
            output_dir / "validated" / f"{table_name}.csv"
        )
        rejected_file = (
            output_dir / "quarantine" / f"{table_name}_rejected.csv"
        )

        # Both output files should exist.
        assert valid_file.exists()
        assert rejected_file.exists()

        valid = pd.read_csv(valid_file)
        rejected = pd.read_csv(rejected_file)

        # File row counts must match the pipeline report.
        assert len(valid) == counts["valid_rows"]
        assert len(rejected) == counts["rejected_rows"]

    # Verify that a JSON report was created for this run.
    report_path = (
        output_dir
        / "reports"
        / f"run_{result['run_id']}.json"
    )

    assert report_path.exists()

    report = json.loads(report_path.read_text())

    assert report["status"] == "SUCCESS"
    assert report["run_id"] == result["run_id"]


def test_rerun_does_not_append_duplicate_rows(tmp_path):
    """Check that rerunning the pipeline does not duplicate business data."""

    output_dir = tmp_path / "rerun_output"

    kwargs = {
        "output_dir": str(output_dir),
        "seed": 42,
        "n_customers": 100,
        "n_products": 20,
        "n_orders": 300,
        "n_order_items": 600,
    }

    # First pipeline execution.
    first = run_pipeline(**kwargs)

    first_customers = pd.read_csv(
        output_dir / "validated" / "customers.csv"
    )

    # Second execution with identical inputs and settings.
    second = run_pipeline(**kwargs)

    second_customers = pd.read_csv(
        output_dir / "validated" / "customers.csv"
    )

    assert first["status"] == "SUCCESS"
    assert second["status"] == "SUCCESS"

    # Remove run-specific metadata before comparing business records.
    # Each execution intentionally creates a different run_id.
    metadata_columns = ["run_id"]

    first_business_data = first_customers.drop(
        columns=metadata_columns
    )

    second_business_data = second_customers.drop(
        columns=metadata_columns
    )

    # The customer business data should be identical.
    pd.testing.assert_frame_equal(
        first_business_data,
        second_business_data,
    )

    # Each execution must have a unique run ID.
    assert first["run_id"] != second["run_id"]

    # Both runs must retain their own reports.
    first_report = (
        output_dir
        / "reports"
        / f"run_{first['run_id']}.json"
    )

    second_report = (
        output_dir
        / "reports"
        / f"run_{second['run_id']}.json"
    )

    assert first_report.exists()
    assert second_report.exists()

    # Verify both reports record successful execution.
    first_report_data = json.loads(first_report.read_text())
    second_report_data = json.loads(second_report.read_text())

    assert first_report_data["status"] == "SUCCESS"
    assert second_report_data["status"] == "SUCCESS"



def test_pipeline_records_failure_for_empty_input(tmp_path):
    """Zero-sized batches must fail loudly and leave a FAILED run report."""

    output_dir = tmp_path / "empty_output"

    with pytest.raises(RuntimeError, match="Pipeline failed"):
        run_pipeline(
            output_dir=str(output_dir),
            n_customers=0,
            n_products=20,
            n_orders=300,
            n_order_items=600,
        )

    reports = list((output_dir / "reports").glob("run_*.json"))
    assert len(reports) == 1

    report = json.loads(reports[0].read_text())
    assert report["status"] == "FAILED"
    assert "All table sizes must be positive" in report["error"]


def test_too_small_bad_record_config_fails_without_publishing(tmp_path):
    """Undersized injection must fail rather than silently grow the table."""

    output_dir = tmp_path / "small_output"

    with pytest.raises(RuntimeError, match="at least 4 order items"):
        run_pipeline(
            output_dir=str(output_dir),
            n_customers=10,
            n_products=5,
            n_orders=10,
            n_order_items=2,
        )

    # Nothing should have been published from a failed run.
    assert not (output_dir / "validated" / "customers.csv").exists()


def test_rejection_reason_counts_and_reconciliation(tmp_path):
    """Report must count each rejection reason and tie to the quarantine file."""

    output_dir = tmp_path / "reasons_output"

    result = run_pipeline(
        output_dir=str(output_dir),
        seed=7,
        n_customers=100,
        n_products=20,
        n_orders=300,
        n_order_items=600,
    )

    order_items = result["tables"]["order_items"]
    quarantine = pd.read_csv(
        output_dir / "quarantine" / "order_items_rejected.csv"
    )

    # A row can fail several rules, so total reasons >= rejected rows.
    # Every quarantined row must carry at least one reason.
    reason_total = sum(order_items["rejections_by_reason"].values())
    assert len(quarantine) == order_items["rejected_rows"]
    assert reason_total >= len(quarantine) > 0
    assert quarantine["rejection_reasons"].notna().all()
    assert order_items["rejections_by_reason"].get(
        "must_be_positive:quantity", 0
    ) == 1
    assert order_items["rejections_by_reason"].get(
        "must_be_positive:unit_price", 0
    ) == 1
    assert order_items["rejections_by_reason"].get(
        "invalid_reference:order_id", 0
    ) >= 1
