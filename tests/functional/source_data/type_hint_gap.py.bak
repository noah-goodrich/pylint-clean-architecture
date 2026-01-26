"""
Type Hint Gap Test File for Mission 3 Smoke Test.

This file contains:
1. A function with clear string return (should be auto-fixed)
2. A function with complex, unhinted dynamic call (should remain unfixed with reported reason)
"""


def clear_string_return():
    """Function that clearly returns a string - should be auto-fixed."""
    return "hello world"


def complex_unhinted_dynamic():
    """Function with complex, unhinted dynamic call - should remain unfixed."""
    # This creates a complex call chain that cannot be deterministically inferred
    data = get_complex_data()
    result = process_dynamic(data)
    return result


def get_complex_data():
    """Helper that returns unknown type."""
    # This would require inference that might fail
    return {"key": "value"}


def process_dynamic(data):
    """Helper that processes data with unknown return type."""
    # This creates a situation where type inference would fail
    return data.get("unknown", None)
