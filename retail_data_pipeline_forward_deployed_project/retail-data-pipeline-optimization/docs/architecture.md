# Architecture and Data Flow

## Purpose
This document describes the implemented local batch pipeline and the separate SQL benchmark.

## Architecture

```text
Deterministic synthetic generator (NumPy / Pandas)
                  |
                  v
       Attach lineage metadata
 source_file, source_row_number, run_id
                  |
                  v
     Validate parent entities first
 customers and products -> orders -> order_items
                  |
          +-------+-------+
          |               |
          v               v
   Valid records     Quarantined records
          |               |
          v               v
 outputs/validated/  outputs/quarantine/
          |
          v
 Load validated CSVs into in-memory DuckDB
          |
          v
 Baseline joins + filters + category aggregation
          |
          v
 Build category-level summary table
          |
          v
 Read optimized summary and compare results
          |
          v
 Benchmark JSON, CSV results, and query plan
```

## Components

| Component | Responsibility | Current implementation |
|---|---|---|
| `generator.py` | Create deterministic synthetic tables and inject known defects | Python, NumPy, Pandas |
| `validation.py` | Apply required-field, type, range, uniqueness, date, enum, and foreign-key checks | Pandas validation functions |
| `pipeline.py` | Assign run ID and lineage, validate in dependency order, reconcile counts, publish outputs, write run report | Local batch execution |
| `optimization.py` | Load validated outputs into DuckDB, run baseline and summary queries, check equality, benchmark repeated query execution | DuckDB + SQL |
| `sql/*.sql` | Human-readable baseline, summary-build, and optimized queries | SQL |
| `tests/` | Verify validation, pipeline, and optimization behavior | Pytest |

## Entity relationships and grain

- `customers`: one row per customer (`customer_id`).
- `products`: one row per product (`product_id`).
- `orders`: one row per order (`order_id`); each order references one customer.
- `order_items`: one row per order line (`order_item_id`); each line references one order and one product.

Relationship flow: `customers 1 -> many orders`; `orders 1 -> many order_items`; `products 1 -> many order_items`.

## Analytical grain and business rules

The report output is one row per product category. Revenue is `SUM(quantity * unit_price)`, units sold is `SUM(quantity)`, and completed orders is the distinct count of completed order IDs represented in each category. Only orders with status `COMPLETED` are included. An order with products from more than one category can contribute to each applicable category's distinct order count.

## Data movement and publication

The pipeline currently generates records internally, validates all tables, checks `input_rows = valid_rows + rejected_rows`, and then writes validated and rejected CSVs. Each run receives a unique UUID and a JSON report. Outputs are written through temporary files and renamed into place; however, the set of multiple output files is not a single atomic transaction.

The benchmark is a separate stage and must run after the pipeline. It reads the validated CSVs and loads the tables into an in-memory DuckDB database. Query timing excludes CSV loading and warm-up execution.

## Current scope boundaries

Implemented: local batch generation, validation, quarantine, run reports, count reconciliation, repeat-run behavior, baseline/summary correctness comparison, and query timing.

Not implemented: external CSV/API ingestion, formal schema version registry, incremental/late-arriving data processing, transactional multi-file publication, persistent database storage, orchestration, and cloud deployment. These are documented future improvements, not claimed as completed capabilities.
