"""Split share calculator for equal bill splitting."""

from typing import List


def calculate_shares(amount: int, n: int) -> List[int]:
    """
    Calculate equal shares for splitting an amount among n participants.
    
    Per spec §9:
    - Shares must be whole minor units
    - Sum exactly to amount
    - Differ by at most one minor unit
    - Larger shares go to first participants in order
    
    Args:
        amount: Total amount in minor units (>= 1, <= 1_000_000_000)
        n: Number of participants (>= 1)
    
    Returns:
        List of n shares in minor units, sum equals amount
    
    Raises:
        ValueError: If amount < 1 or n < 1
    """
    if amount < 1:
        raise ValueError("amount must be >= 1")
    if n < 1:
        raise ValueError("n must be >= 1")
    
    # Base share for each participant
    base_share = amount // n
    # Remainder goes to first participants
    remainder = amount % n
    
    shares = []
    for i in range(n):
        if i < remainder:
            shares.append(base_share + 1)
        else:
            shares.append(base_share)
    
    return shares


def validate_shares(shares: List[int], amount: int) -> bool:
    """
    Validate that shares meet the spec requirements.
    
    Returns:
        True if valid, False otherwise
    """
    if not shares:
        return False
    
    # Sum equals amount
    if sum(shares) != amount:
        return False
    
    # All non-negative
    if any(s < 0 for s in shares):
        return False
    
    # Diff at most 1
    if shares:
        max_share = max(shares)
        min_share = min(shares)
        if max_share - min_share > 1:
            return False
    
    # Larger shares first (non-increasing)
    for i in range(1, len(shares)):
        if shares[i] > shares[i - 1]:
            return False
    
    return True


# Test the implementation
if __name__ == "__main__":
    # Test cases from spec §9
    test_cases = [
        (1000, 3, [334, 333, 333]),
        (1, 3, [1, 0, 0]),
        (10, 3, [4, 3, 3]),
        (999, 3, [333, 333, 333]),
        (5, 5, [1, 1, 1, 1, 1]),
    ]
    
    for amount, n, expected in test_cases:
        result = calculate_shares(amount, n)
        assert result == expected, f"Failed: calculate_shares({amount}, {n}) = {result}, expected {expected}"
        assert validate_shares(result, amount), f"Invalid shares: {result} for amount {amount}"
        print(f"calculate_shares({amount}, {n}) = {result} OK")
    
    # Additional edge cases
    assert calculate_shares(100, 1) == [100]
    assert calculate_shares(100, 2) == [50, 50]
    assert calculate_shares(101, 2) == [51, 50]
    assert calculate_shares(999999999, 32) == [31250000] * 31 + [31249999]  # 32 participants
    
    # Large number of participants
    shares = calculate_shares(1000, 1000)
    assert shares == [1] * 1000
    assert validate_shares(shares, 1000)
    
    shares = calculate_shares(1000, 1001)
    assert shares == [1] * 1000 + [0]
    assert validate_shares(shares, 1000)
    
    # Error cases
    try:
        calculate_shares(0, 3)
        assert False, "Should have raised"
    except ValueError as e:
        assert "amount must be >= 1" in str(e)
    
    try:
        calculate_shares(100, 0)
        assert False, "Should have raised"
    except ValueError as e:
        assert "n must be >= 1" in str(e)
    
    print("\nAll split share calculator tests passed!")