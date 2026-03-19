"""
Tests for _parse_form_value_with_schema in api_v3.py.

The function is module-level so we import it directly.
"""
import sys
import os

# Ensure LEDMatrix root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('EMULATOR', 'true')

from web_interface.blueprints.api_v3 import _parse_form_value_with_schema


STRING_SCHEMA = {
    "properties": {
        "station_id": {"type": "string", "default": ""}
    }
}

INTEGER_SCHEMA = {
    "properties": {
        "window_minutes": {"type": "integer", "default": 30}
    }
}

NULLABLE_STRING_SCHEMA = {
    "properties": {
        "station_id": {"type": ["string", "null"], "default": None}
    }
}


def test_numeric_string_stays_string_when_schema_says_string():
    """'65' must not be coerced to integer 65 when field type is string."""
    result = _parse_form_value_with_schema("65", "station_id", STRING_SCHEMA)
    assert result == "65", f"Expected '65' (str), got {result!r} ({type(result).__name__})"
    assert isinstance(result, str), f"Expected str, got {type(result).__name__}"


def test_alphanumeric_string_unchanged():
    """'B18' should pass through as-is."""
    result = _parse_form_value_with_schema("B18", "station_id", STRING_SCHEMA)
    assert result == "B18"


def test_empty_string_for_string_field():
    """Empty string is a valid value for an optional string field."""
    result = _parse_form_value_with_schema("", "station_id", STRING_SCHEMA)
    assert result == ""


def test_integer_field_still_coerced():
    """Integer fields should still be coerced from strings."""
    result = _parse_form_value_with_schema("30", "window_minutes", INTEGER_SCHEMA)
    assert result == 30
    assert isinstance(result, int)


def test_numeric_string_no_schema_coerced():
    """With no schema prop, numeric strings are still coerced (existing behaviour)."""
    result = _parse_form_value_with_schema("42", "unknown_field", {})
    assert result == 42
    assert isinstance(result, int)


def test_numeric_string_stays_string_when_schema_says_nullable_string():
    """'65' must not be coerced when field type is ["string", "null"]."""
    result = _parse_form_value_with_schema("65", "station_id", NULLABLE_STRING_SCHEMA)
    assert result == "65"
    assert isinstance(result, str)
