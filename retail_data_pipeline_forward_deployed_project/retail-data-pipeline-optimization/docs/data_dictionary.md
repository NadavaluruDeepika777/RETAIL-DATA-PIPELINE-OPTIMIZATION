# Data Dictionary

## 1. customers

| Column | Meaning | Rule |
|---|---|---|
| customer_id | Unique customer identifier | Required, unique |
| customer_name | Customer name | Required |
| city | Customer city | Nullable (optional) |
| signup_date | Customer signup date | Required, ISO-8601 date |

## 2. products

| Column | Meaning | Rule |
|---|---|---|
| product_id | Unique product identifier | Required, unique |
| product_name | Product name | Required |
| category | Product category | Required |
| unit_price | Product unit price | Required, greater than zero |

## 3. orders

| Column | Meaning | Rule |
|---|---|---|
| order_id | Unique order identifier | Required, unique |
| customer_id | Customer who placed the order | Must reference customers |
| order_date | Order date | Required, ISO-8601 date |
| status | Order status | COMPLETED, CANCELLED, or PENDING |

## 4. order_items

| Column | Meaning | Rule |
|---|---|---|
| order_item_id | Unique order-item identifier | Required, unique |
| order_id | Parent order identifier | Must reference orders |
| product_id | Purchased product identifier | Must reference products |
| quantity | Number of units | Required, whole number greater than zero |
| unit_price | Price recorded for the order item | Required, greater than zero |

## 5. Pipeline Metadata

Validated and rejected records may also contain:

| Column | Meaning |
|---|---|
| source_file | Source associated with the record |
| source_row_number | Original data row number |
| run_id | Identifier for the pipeline execution |
| rejection_reasons | Every rule the rejected record failed, separated by `; ` |

The metadata columns support traceability and debugging.

## 6. Relationships

- `orders.customer_id` references `customers.customer_id`.
- `order_items.order_id` references `orders.order_id`.
- `order_items.product_id` references `products.product_id`.

## 7. Metric Rules

Revenue is calculated as:

`SUM(quantity * unit_price)`

Only records belonging to `COMPLETED` orders contribute to the category
revenue, units-sold, and completed-order metrics.

Completed orders are counted distinctly within each product category.
An order containing products from multiple categories can therefore
contribute to more than one category's completed-order count.

## 8. Rejection Reason Codes

| Code | Meaning |
|---|---|
| missing_required:<column> | Null or whitespace-only required value |
| must_be_numeric:<column> | Value cannot be read as a number |
| must_be_positive:<column> | Numeric value is zero or negative |
| must_be_integer:<column> | Numeric value has a fractional part |
| invalid_date:<column> | Value is not an ISO-8601 date |
| invalid_value:<column> | Value is outside the allowed set |
| invalid_reference:<column> | Parent key is missing or was itself rejected |
| duplicate_primary_key:<column> | An earlier field-clean row already holds this key |
