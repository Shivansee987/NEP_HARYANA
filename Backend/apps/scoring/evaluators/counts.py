"""
NEP Excellence Awards 2026 - Count Quantity Validator
Enforces integer count semantics across count-based quantities (patents, startups, programmes, etc.)
Rejects fractional values (e.g. 1.5, 2.5) and negative counts while accepting valid integral representations.
"""
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple


def validate_count_quantity(
    value: Any,
    field_name: str = "count",
    allow_zero: bool = True
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validates that a count-based quantity is a non-negative integer.

    Returns:
        (is_valid, sanitized_int_count, error_message)
    """
    if value is None:
        if allow_zero:
            return True, 0, None
        return False, None, f"{field_name} is required."

    # In Python, bool is a subclass of int (True == 1, False == 0).
    # Explicitly reject boolean values for count quantities.
    if isinstance(value, bool):
        return False, None, f"Boolean value {value} is not a valid integer count for {field_name}."

    # Handle native integers
    if isinstance(value, int):
        if value < 0:
            return False, None, f"Negative count {value} rejected for {field_name}: counts must be non-negative."
        if value == 0 and not allow_zero:
            return False, None, f"Count of 0 rejected for {field_name} (non-zero required)."
        return True, value, None

    # Handle floats and Decimals
    if isinstance(value, (float, Decimal)):
        try:
            val_float = float(value)
        except (ValueError, OverflowError):
            return False, None, f"Invalid numeric value for {field_name}."

        if val_float < 0.0:
            return False, None, f"Negative count {value} rejected for {field_name}: counts must be non-negative."

        if val_float.is_integer():
            int_val = int(val_float)
            if int_val == 0 and not allow_zero:
                return False, None, f"Count of 0 rejected for {field_name} (non-zero required)."
            return True, int_val, None
        else:
            return False, None, f"Fractional count {value} rejected for {field_name}: counts must be whole integers."

    # Handle string representations
    if isinstance(value, str):
        val_str = value.strip()
        try:
            val_float = float(val_str)
        except ValueError:
            return False, None, f"Non-numeric string '{value}' rejected for {field_name}."

        if val_float < 0.0:
            return False, None, f"Negative count '{value}' rejected for {field_name}: counts must be non-negative."

        if val_float.is_integer():
            int_val = int(val_float)
            if int_val == 0 and not allow_zero:
                return False, None, f"Count of 0 rejected for {field_name} (non-zero required)."
            return True, int_val, None
        else:
            return False, None, f"Fractional count '{value}' rejected for {field_name}: counts must be whole integers."

    return False, None, f"Unsupported data type {type(value).__name__} for count quantity {field_name}."
