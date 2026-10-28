import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "src")
)

from retail_pipeline.validation import validate_table


def customer_data():
    return pd.DataFrame({
        "customer_id": [1, 2, 2, 4],
        "customer_name": ["A", "B", "Duplicate B", None],
        "signup_date": pd.to_datetime([
            "2025-01-01",
            "2025-01-02",
            "2025-01-03",
            "2025-01-04",
        ]),
    })


def test_duplicate_and_missing_values():
    valid, rejected = validate_table(
        customer_data(),
        primary_key="customer_id",
        required_columns=[
            "customer_id", "customer_name", "signup_date"
        ],
    )

    assert len(valid) == 2
    assert len(rejected) == 2
    assert "duplicate_primary_key" in rejected.iloc[0][
        "rejection_reasons"
    ]
    assert "missing_required:customer_name" in rejected.iloc[1][
        "rejection_reasons"
    ]


def test_empty_dataframe():
    df = pd.DataFrame({
        "customer_id": pd.Series(dtype="int64"),
        "customer_name": pd.Series(dtype="object"),
        "signup_date": pd.Series(dtype="datetime64[ns]"),
    })

    valid, rejected = validate_table(
        df,
        primary_key="customer_id",
        required_columns=[
            "customer_id", "customer_name", "signup_date"
        ],
    )

    assert valid.empty
    assert rejected.empty


def test_invalid_foreign_key():
    orders = pd.DataFrame({
        "order_id": [1],
        "customer_id": [999],
        "order_date": pd.to_datetime(["2025-01-01"]),
        "status": ["COMPLETED"],
    })

    valid, rejected = validate_table(
        orders,
        primary_key="order_id",
        required_columns=[
            "order_id", "customer_id", "order_date", "status"
        ],
        foreign_keys={"customer_id": {1, 2}},
    )

    assert valid.empty
    assert len(rejected) == 1
    assert "invalid_reference:customer_id" in rejected.iloc[0][
        "rejection_reasons"
    ]


def test_missing_schema_column_fails_explicitly():
    df = pd.DataFrame({"customer_id": [1]})

    with pytest.raises(ValueError, match="Missing required column"):
        validate_table(
            df,
            primary_key="customer_id",
            required_columns=["customer_id", "customer_name"],
        )


def test_non_positive_quantity():
    items = pd.DataFrame({
        "order_item_id": [1, 2],
        "quantity": [1, 0],
    })

    valid, rejected = validate_table(
        items,
        primary_key="order_item_id",
        required_columns=["order_item_id", "quantity"],
        positive_columns=["quantity"],
    )

    assert len(valid) == 1
    assert len(rejected) == 1
    assert "must_be_positive:quantity" in rejected.iloc[0][
        "rejection_reasons"
    ]


def test_non_numeric_values_are_rejected_not_passed():
    """Malformed numbers must fail, not silently skip the positive check."""
    df = pd.DataFrame({
        "product_id": [1, 2],
        "unit_price": ["abc", 5.0],
    })

    valid, rejected = validate_table(
        df,
        primary_key="product_id",
        required_columns=["product_id", "unit_price"],
        positive_columns=["unit_price"],
    )

    assert valid["product_id"].tolist() == [2]
    assert "must_be_numeric:unit_price" in rejected.iloc[0][
        "rejection_reasons"
    ]


def test_fractional_quantity_rejected_when_integer_required():
    df = pd.DataFrame({
        "order_item_id": [1, 2, 3],
        "quantity": ["x", 1.5, 2],
    })

    valid, rejected = validate_table(
        df,
        primary_key="order_item_id",
        required_columns=["order_item_id", "quantity"],
        positive_columns=["quantity"],
        integer_columns=["quantity"],
    )

    assert valid["order_item_id"].tolist() == [3]
    reasons = " ".join(rejected["rejection_reasons"])
    assert "must_be_numeric:quantity" in reasons
    assert "must_be_integer:quantity" in reasons


def test_whitespace_only_text_counts_as_missing():
    df = pd.DataFrame({
        "customer_id": [1, 2],
        "customer_name": ["   ", "Valid"],
    })

    valid, rejected = validate_table(
        df,
        primary_key="customer_id",
        required_columns=["customer_id", "customer_name"],
    )

    assert valid["customer_id"].tolist() == [2]
    assert "missing_required:customer_name" in rejected.iloc[0][
        "rejection_reasons"
    ]


def test_invalid_date_is_rejected():
    orders = pd.DataFrame({
        "order_id": [1, 2],
        "order_date": ["not-a-date", "2025-01-01"],
    })

    valid, rejected = validate_table(
        orders,
        primary_key="order_id",
        required_columns=["order_id", "order_date"],
        date_columns=["order_date"],
    )

    assert valid["order_id"].tolist() == [2]
    assert "invalid_date:order_date" in rejected.iloc[0][
        "rejection_reasons"
    ]


def test_valid_duplicate_survives_invalid_first_copy():
    """An invalid first copy must not cause the clean later copy to be lost."""
    df = pd.DataFrame({
        "customer_id": [1, 1],
        "customer_name": [None, "Real Name"],
        "signup_date": ["2025-01-01", "2025-01-02"],
    })

    valid, rejected = validate_table(
        df,
        primary_key="customer_id",
        required_columns=["customer_id", "customer_name", "signup_date"],
    )

    assert valid["customer_name"].tolist() == ["Real Name"]
    assert len(rejected) == 1
    assert "missing_required:customer_name" in rejected.iloc[0][
        "rejection_reasons"
    ]


def test_only_first_clean_copy_is_kept_among_duplicates():
    df = pd.DataFrame({
        "customer_id": [5, 5, 5],
        "customer_name": ["first", "second", "third"],
    })

    valid, rejected = validate_table(
        df,
        primary_key="customer_id",
        required_columns=["customer_id", "customer_name"],
    )

    assert valid["customer_name"].tolist() == ["first"]
    assert len(rejected) == 2
    assert all(
        "duplicate_primary_key:customer_id" in reason
        for reason in rejected["rejection_reasons"]
    )


def test_empty_frame_with_date_and_integer_rules():
    df = pd.DataFrame({
        "order_item_id": pd.Series(dtype="int64"),
        "quantity": pd.Series(dtype="int64"),
        "order_date": pd.Series(dtype="object"),
    })

    valid, rejected = validate_table(
        df,
        primary_key="order_item_id",
        required_columns=["order_item_id", "quantity", "order_date"],
        positive_columns=["quantity"],
        integer_columns=["quantity"],
        date_columns=["order_date"],
    )

    assert valid.empty
    assert rejected.empty
    assert "rejection_reasons" in rejected.columns
