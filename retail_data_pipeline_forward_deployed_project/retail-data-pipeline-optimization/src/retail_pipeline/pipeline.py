"""End-to-end retail data-quality pipeline.

Flow: generate source tables -> attach lineage -> validate parents before
children -> reconcile counts -> publish validated and quarantined CSVs ->
write a JSON run report. Every run writes a report, including failed runs.
"""

import argparse
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from retail_pipeline.generator import generate_retail_data
from retail_pipeline.validation import validate_table


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _reason_counts(rejected):
    """Count how many times each rejection reason occurs in a table."""
    if rejected.empty:
        return {}
    reasons = rejected["rejection_reasons"].str.split("; ").explode()
    return {
        str(reason): int(count)
        for reason, count in reasons.value_counts().sort_index().items()
    }


def _validate_all(sources):
    """Validate parent tables first so child checks use valid parent keys."""
    valid_customers, rejected_customers = validate_table(
        sources["customers"],
        "customer_id",
        ["customer_id", "customer_name", "signup_date"],
        date_columns=["signup_date"],
    )

    valid_products, rejected_products = validate_table(
        sources["products"],
        "product_id",
        ["product_id", "product_name", "category", "unit_price"],
        positive_columns=["unit_price"],
    )

    valid_orders, rejected_orders = validate_table(
        sources["orders"],
        "order_id",
        ["order_id", "customer_id", "order_date", "status"],
        date_columns=["order_date"],
        allowed_values={"status": {"COMPLETED", "CANCELLED", "PENDING"}},
        foreign_keys={"customer_id": set(valid_customers["customer_id"])},
    )

    valid_order_items, rejected_order_items = validate_table(
        sources["order_items"],
        "order_item_id",
        ["order_item_id", "order_id", "product_id", "quantity", "unit_price"],
        positive_columns=["quantity", "unit_price"],
        integer_columns=["quantity"],
        foreign_keys={
            "order_id": set(valid_orders["order_id"]),
            "product_id": set(valid_products["product_id"]),
        },
    )

    valid = {
        "customers": valid_customers,
        "products": valid_products,
        "orders": valid_orders,
        "order_items": valid_order_items,
    }
    rejected = {
        "customers": rejected_customers,
        "products": rejected_products,
        "orders": rejected_orders,
        "order_items": rejected_order_items,
    }
    return valid, rejected


def run_pipeline(
    output_dir="outputs",
    seed=42,
    n_customers=1000,
    n_products=100,
    n_orders=5000,
    n_order_items=10000,
    include_bad_records=True,
):
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    start = time.perf_counter()

    output_path = Path(output_dir)
    valid_dir = output_path / "validated"
    quarantine_dir = output_path / "quarantine"
    report_dir = output_path / "reports"

    for directory in [valid_dir, quarantine_dir, report_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    summary = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "status": "RUNNING",
        "tables": {},
    }
    report_file = report_dir / f"run_{run_id}.json"

    try:
        raw_tables = generate_retail_data(
            n_customers=n_customers,
            n_products=n_products,
            n_orders=n_orders,
            n_order_items=n_order_items,
            seed=seed,
            include_bad_records=include_bad_records,
        )

        # Attach lineage: file name and original 1-based CSV row number
        # (row 1 is the header, so the first data row is row 2).
        sources = {}
        for name, df in raw_tables.items():
            source = df.copy()
            source["source_file"] = f"{name}.csv"
            source["source_row_number"] = range(2, len(source) + 2)
            source["run_id"] = run_id
            sources[name] = source

        valid_tables, rejected_tables = _validate_all(sources)

        # Reconcile every table BEFORE publishing anything, so a mismatch
        # cannot leave some tables updated and others stale.
        for name in raw_tables:
            raw_count = len(raw_tables[name])
            valid_count = len(valid_tables[name])
            rejected_count = len(rejected_tables[name])

            if raw_count != valid_count + rejected_count:
                raise RuntimeError(f"Reconciliation failed for {name}")

            summary["tables"][name] = {
                "input_rows": raw_count,
                "valid_rows": valid_count,
                "rejected_rows": rejected_count,
                "rejections_by_reason": _reason_counts(rejected_tables[name]),
            }

        # Publish through temporary files, then replace. A crash mid-write
        # leaves a .tmp file rather than a half-written CSV.
        for name in raw_tables:
            valid_file = valid_dir / f"{name}.csv"
            reject_file = quarantine_dir / f"{name}_rejected.csv"

            valid_tmp = valid_file.with_suffix(".csv.tmp")
            reject_tmp = reject_file.with_suffix(".csv.tmp")

            valid_tables[name].to_csv(valid_tmp, index=False)
            rejected_tables[name].to_csv(reject_tmp, index=False)

            valid_tmp.replace(valid_file)
            reject_tmp.replace(reject_file)

        summary["status"] = "SUCCESS"

    except Exception as exc:
        summary["status"] = "FAILED"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        logger.exception("Pipeline run failed")

    finally:
        summary["ended_at"] = datetime.now(timezone.utc).isoformat()
        summary["duration_seconds"] = round(
            time.perf_counter() - start, 6
        )
        report_file.write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Run %s finished with status %s", run_id, summary["status"]
        )

    if summary["status"] != "SUCCESS":
        raise RuntimeError(
            f"Pipeline failed: {summary['error']}. "
            f"Run report: {report_file}"
        )

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Retail data-quality pipeline"
    )
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--products", type=int, default=100)
    parser.add_argument("--orders", type=int, default=5000)
    parser.add_argument("--order-items", type=int, default=10000)
    parser.add_argument(
        "--clean-data",
        action="store_true",
        help="Generate valid data without injected quality defects",
    )

    args = parser.parse_args()

    result = run_pipeline(
        output_dir=args.output_dir,
        seed=args.seed,
        n_customers=args.customers,
        n_products=args.products,
        n_orders=args.orders,
        n_order_items=args.order_items,
        include_bad_records=not args.clean_data,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
