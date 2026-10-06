"""Currency formatting utilities for minor unit handling."""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Tuple

# Supported currencies with their minor units
CURRENCY_MINOR_UNITS = {
    "EUR": 2,
    "JPY": 0,
    "BHD": 3,
}


class CurrencyError(ValueError):
    """Raised when currency formatting/parsing fails."""
    pass


def get_minor_units(currency: str) -> int:
    """Get the number of minor units for a currency."""
    if currency not in CURRENCY_MINOR_UNITS:
        raise CurrencyError(f"Unsupported currency: {currency}")
    return CURRENCY_MINOR_UNITS[currency]


def format_amount(minor_units: int, currency: str) -> str:
    """
    Format minor units as a human-readable amount with currency code.
    
    Args:
        minor_units: Amount in minor units (e.g., 1500 for 15.00 EUR)
        currency: Currency code (EUR, JPY, BHD)
    
    Returns:
        Formatted string like "15.00 EUR" or "1500 JPY"
    
    Raises:
        CurrencyError: If currency is unsupported or minor_units is negative
    """
    if minor_units < 0:
        raise CurrencyError("Amount cannot be negative")
    
    dp = get_minor_units(currency)
    
    if dp == 0:
        return f"{minor_units} {currency}"
    
    # Convert to major units
    divisor = 10 ** dp
    major = minor_units // divisor
    minor = minor_units % divisor
    
    # Format with leading zeros for minor part
    minor_str = str(minor).zfill(dp)
    
    return f"{major}.{minor_str} {currency}"


def parse_amount(amount_str: str, currency: str) -> int:
    """
    Parse a human-readable amount string into minor units.
    
    Args:
        amount_str: Amount string like "15.00" or "1500"
        currency: Currency code (EUR, JPY, BHD)
    
    Returns:
        Amount in minor units (e.g., 1500 for "15.00" EUR)
    
    Raises:
        CurrencyError: If currency is unsupported, amount is invalid,
                       or has too many decimal places
    """
    if not amount_str or not isinstance(amount_str, str):
        raise CurrencyError("Amount string is required")
    
    dp = get_minor_units(currency)
    amount_str = amount_str.strip()
    
    if dp == 0:
        # For JPY, only integers allowed
        try:
            value = int(amount_str)
            if value < 0:
                raise CurrencyError("Amount cannot be negative")
            return value
        except ValueError:
            raise CurrencyError(f"Invalid amount for {currency}: must be an integer")
    
    # For currencies with decimal places, validate decimal precision
    if "." in amount_str:
        parts = amount_str.split(".")
        if len(parts) != 2:
            raise CurrencyError("Invalid amount format")
        
        integer_part, decimal_part = parts
        
        # Check decimal places don't exceed currency precision
        if len(decimal_part) > dp:
            raise CurrencyError(
                f"Too many decimal places for {currency}: "
                f"max {dp}, got {len(decimal_part)}"
            )
        
        # Check for rounding issues (e.g., 15.005 for 2dp)
        if len(decimal_part) == dp:
            # Check if there would be rounding needed
            # Pad to check next digit
            pass  # Already exact
        
        # Combine and convert
        try:
            # Remove decimal point and pad decimal part
            padded_decimal = decimal_part.ljust(dp, '0')
            full_amount = int(integer_part + padded_decimal)
            if full_amount < 0:
                raise CurrencyError("Amount cannot be negative")
            return full_amount
        except ValueError:
            raise CurrencyError("Invalid amount format")
    else:
        # No decimal point, treat as whole major units
        try:
            major = int(amount_str)
        except ValueError:
            raise CurrencyError("Invalid amount format")
        
        if major < 0:
            raise CurrencyError("Amount cannot be negative")
        return major * (10 ** dp)


def validate_amount(amount_str: str, currency: str) -> Tuple[bool, str]:
    """
    Validate an amount string for a currency without parsing.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parse_amount(amount_str, currency)
        return True, ""
    except CurrencyError as e:
        return False, str(e)


# Test the implementation
if __name__ == "__main__":
    # Test format_amount
    assert format_amount(10000, "EUR") == "100.00 EUR"
    assert format_amount(1500, "EUR") == "15.00 EUR"
    assert format_amount(1000, "JPY") == "1000 JPY"
    assert format_amount(12345, "BHD") == "12.345 BHD"
    assert format_amount(0, "EUR") == "0.00 EUR"
    assert format_amount(1, "EUR") == "0.01 EUR"
    assert format_amount(99, "EUR") == "0.99 EUR"
    print("format_amount tests passed")
    
    # Test parse_amount
    assert parse_amount("100.00", "EUR") == 10000
    assert parse_amount("15.00", "EUR") == 1500
    assert parse_amount("1000", "JPY") == 1000
    assert parse_amount("12.345", "BHD") == 12345
    assert parse_amount("0", "EUR") == 0
    assert parse_amount("0.00", "EUR") == 0
    assert parse_amount("0.01", "EUR") == 1
    assert parse_amount("0.99", "EUR") == 99
    assert parse_amount("15", "EUR") == 1500
    assert parse_amount("15.5", "EUR") == 1550
    print("parse_amount tests passed")
    
    # Test validation errors
    try:
        parse_amount("15.005", "EUR")
        assert False, "Should have raised"
    except CurrencyError as e:
        assert "Too many decimal places" in str(e)
    
    try:
        parse_amount("-100", "EUR")
        assert False, "Should have raised"
    except CurrencyError as e:
        assert "negative" in str(e)
    
    try:
        parse_amount("15.005", "JPY")
        assert False, "Should have raised"
    except CurrencyError as e:
        assert "integer" in str(e)
    
    print("validation tests passed")
    print("All currency tests passed!")