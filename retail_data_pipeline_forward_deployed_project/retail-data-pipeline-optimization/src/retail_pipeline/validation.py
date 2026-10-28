"""Row-level data-quality validation for the retail pipeline.

Every input row is either returned in ``valid`` or in ``rejected``; each
rejected row carries a ``rejection_reasons`` string listing every rule it
failed. Nothing is silently dropped.
"""

import numpy as np
import pandas as pd


def _blank_mask(series):
    """True where a value is missing, or is a string that is only whitespace."""
    missing = series.isna().to_numpy()
    if series.dtype == object or pd.api.types.is_string_dtype(series):
        blank_text = series.map(
            lambda value: isinstance(value, str) and value.strip() == ""
        ).to_numpy(dtype=bool)
        return missing | blank_text
    return missing


def _flag(reasons, mask, message):
    """Append ``message`` to the reasons of every row where ``mask`` is True."""
    for position in np.flatnonzero(np.asarray(mask, dtype=bool)):
        reasons[position].append(message)


def validate_table(
    df,
    primary_key,
    required_columns,
    positive_columns=None,
    integer_columns=None,
    date_columns=None,
    allowed_values=None,
    foreign_keys=None,
):
    """
    Return ``(valid_rows, rejected_rows)``.

    Checks, in order:

    * required columns are present and not blank (null or whitespace-only);
    * ``positive_columns`` are numeric and strictly greater than zero;
    * ``integer_columns`` are numeric whole numbers;
    * ``date_columns`` parse as ISO-8601 dates;
    * ``allowed_values`` maps a column to its permitted set of values;
    * ``foreign_keys`` maps a column to the set of valid parent IDs;
    * the primary key is unique among rows that pass every check above.

    The first occurrence of a duplicated key that passes field-level checks
    is kept. A later duplicate is rejected. If the first occurrence is itself
    invalid, the next clean occurrence is kept, so a valid record is not lost
    because an invalid copy appeared earlier. Original row values are preserved.

    Raises ``ValueError`` if a column named in any rule is missing from ``df``.
    """
    positive_columns = positive_columns or []
    integer_columns = integer_columns or []
    date_columns = date_columns or []
    allowed_values = allowed_values or {}
    foreign_keys = foreign_keys or {}

    result = df.copy().reset_index(drop=True)
    reasons = [[] for _ in range(len(result))]

    def require_columns(columns):
        for column in columns:
            if column not in result.columns:
                raise ValueError(f"Missing required column: {column}")

    require_columns(required_columns)
    require_columns([primary_key])
    require_columns(positive_columns)
    require_columns(integer_columns)
    require_columns(date_columns)
    require_columns(allowed_values)
    require_columns(foreign_keys)

    # 1. Required fields (null or whitespace-only counts as missing).
    for column in required_columns:
        _flag(
            reasons,
            _blank_mask(result[column]),
            f"missing_required:{column}",
        )

    # 2. Numeric checks: non-numeric text is malformed, not "unchecked".
    for column in dict.fromkeys(positive_columns + integer_columns):
        blank = _blank_mask(result[column])
        numeric = pd.to_numeric(result[column], errors="coerce")
        numeric_values = numeric.to_numpy(dtype=float, na_value=np.nan)
        not_numeric = ~blank & np.isnan(numeric_values)
        _flag(reasons, not_numeric, f"must_be_numeric:{column}")

        if column in positive_columns:
            _flag(
                reasons,
                ~np.isnan(numeric_values) & (numeric_values <= 0),
                f"must_be_positive:{column}",
            )
        if column in integer_columns:
            _flag(
                reasons,
                ~np.isnan(numeric_values) & (numeric_values % 1 != 0),
                f"must_be_integer:{column}",
            )

    # 3. Date checks.
    for column in date_columns:
        blank = _blank_mask(result[column])
        parsed = pd.to_datetime(
            result[column], errors="coerce", format="ISO8601"
        )
        _flag(
            reasons,
            ~blank & parsed.isna().to_numpy(),
            f"invalid_date:{column}",
        )

    # 4. Allowed values.
    for column, permitted in allowed_values.items():
        blank = _blank_mask(result[column])
        _flag(
            reasons,
            ~blank & ~result[column].isin(permitted).to_numpy(),
            f"invalid_value:{column}",
        )

    # 5. Referential integrity against already-validated parent keys.
    for column, valid_parent_ids in foreign_keys.items():
        blank = _blank_mask(result[column])
        _flag(
            reasons,
            ~blank & ~result[column].isin(valid_parent_ids).to_numpy(),
            f"invalid_reference:{column}",
        )

    # 6. Primary-key uniqueness, decided only among field-clean rows.
    field_clean = np.array([not row for row in reasons], dtype=bool)
    keyed_clean = result.loc[field_clean & ~_blank_mask(result[primary_key])]
    duplicate_positions = keyed_clean.index[
        keyed_clean[primary_key].duplicated(keep="first")
    ]
    for label in duplicate_positions:
        reasons[label].append(f"duplicate_primary_key:{primary_key}")

    rejected_mask = np.array([bool(row) for row in reasons], dtype=bool)

    rejected = result.loc[rejected_mask].copy()
    rejected["rejection_reasons"] = [
        "; ".join(reasons[position])
        for position in np.flatnonzero(rejected_mask)
    ]

    valid = result.loc[~rejected_mask].copy()

    return valid, rejected
