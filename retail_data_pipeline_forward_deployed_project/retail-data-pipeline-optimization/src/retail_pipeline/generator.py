import numpy as np
import pandas as pd


def generate_retail_data(
    n_customers=1000,
    n_products=100,
    n_orders=5000,
    n_order_items=10000,
    seed=42,
    include_bad_records=True,
):
    """Generate deterministic synthetic retail tables."""
    if min(n_customers, n_products, n_orders, n_order_items) < 1:
        raise ValueError("All table sizes must be positive.")

    # Bad-record injection writes to fixed row positions 0-3 of order_items,
    # so it needs at least four rows. Without this guard, .loc would silently
    # append new rows and corrupt the requested table size.
    if include_bad_records and n_order_items < 4:
        raise ValueError(
            "include_bad_records requires at least 4 order items."
        )

    rng = np.random.default_rng(seed)

    customers = pd.DataFrame({
        "customer_id": np.arange(1, n_customers + 1),
        "customer_name": [
            f"Customer_{i}" for i in range(1, n_customers + 1)
        ],
        "city": rng.choice(
            ["Bengaluru", "Chennai", "Hyderabad", "Mumbai", None],
            size=n_customers,
        ),
        "signup_date": pd.to_datetime(
            rng.integers(
                pd.Timestamp("2024-01-01").value // 10**9,
                pd.Timestamp("2026-01-01").value // 10**9,
                size=n_customers,
            ),
            unit="s",
        ).normalize(),
    })

    products = pd.DataFrame({
        "product_id": np.arange(1, n_products + 1),
        "product_name": [
            f"Product_{i}" for i in range(1, n_products + 1)
        ],
        "category": rng.choice(
            ["Electronics", "Home", "Fashion", "Books"],
            size=n_products,
        ),
        "unit_price": np.round(
            rng.uniform(50, 5000, size=n_products), 2
        ),
    })

    orders = pd.DataFrame({
        "order_id": np.arange(1, n_orders + 1),
        "customer_id": rng.integers(
            1, n_customers + 1, size=n_orders
        ),
        "order_date": pd.to_datetime(
            rng.integers(
                pd.Timestamp("2025-01-01").value // 10**9,
                pd.Timestamp("2026-10-01").value // 10**9,
                size=n_orders,
            ),
            unit="s",
        ),
        "status": rng.choice(
            ["COMPLETED", "CANCELLED", "PENDING"],
            size=n_orders,
            p=[0.75, 0.15, 0.10],
        ),
    })

    order_items = pd.DataFrame({
        "order_item_id": np.arange(1, n_order_items + 1),
        "order_id": rng.integers(
            1, n_orders + 1, size=n_order_items
        ),
        "product_id": rng.integers(
            1, n_products + 1, size=n_order_items
        ),
        "quantity": rng.integers(1, 6, size=n_order_items),
    })

    prices = products.set_index("product_id")["unit_price"]
    order_items["unit_price"] = (
        order_items["product_id"].map(prices).astype(float)
    )

    if include_bad_records:
        customers = pd.concat(
            [customers, customers.iloc[[0]]],
            ignore_index=True,
        )
        customers.loc[
            len(customers) - 1, "customer_name"
        ] = None

        orders.loc[0, "customer_id"] = n_customers + 999
        order_items.loc[0, "order_id"] = n_orders + 999
        order_items.loc[1, "product_id"] = n_products + 999
        order_items.loc[2, "quantity"] = 0
        order_items.loc[3, "unit_price"] = -10.00

    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
    }
