import pytest
import os
from .year_range import YearRange

def test_year_range_init():
    """Test basic initialization of YearRange objects."""
    # Test with year range format
    yr = YearRange("2020-2023.json")
    assert yr.filename == "2020-2023.json"
    assert yr.start_year == 2020
    assert yr.end_year == 2023
    assert yr.single_year is None

    # Test with default file
    yr = YearRange("default.json")
    assert yr.start_year == 0
    assert yr.end_year == 9999
    assert yr.single_year is None

def test_year_range_with_path():
    """Test YearRange initialization with full paths."""
    # Test with full path
    yr = YearRange("/path/to/2018-2022.json")
    assert yr.filename == "/path/to/2018-2022.json"
    assert yr.start_year == 2018
    assert yr.end_year == 2022

    # Test with relative path
    yr = YearRange("folder/2019-2021.json")
    assert yr.filename == "folder/2019-2021.json"
    assert yr.start_year == 2019
    assert yr.end_year == 2021

def test_contains_year():
    """Test the contains_year functionality."""
    # Test year range
    yr = YearRange("2020-2025.json")
    assert yr.contains_year(2020) is True
    assert yr.contains_year(2022) is True
    assert yr.contains_year(2025) is True
    assert yr.contains_year(2019) is False
    assert yr.contains_year(2026) is False

    # Test default range (should include all years)
    yr = YearRange("default.json")
    assert yr.contains_year(1950) is True
    assert yr.contains_year(2000) is True
    assert yr.contains_year(2030) is True

def test_string_representation():
    """Test the string representation of YearRange objects."""
    # Test year range string rep
    yr = YearRange("2020-2025.json")
    assert str(yr) == "2020-2025 (2020-2025.json)"

    # Test default string rep
    yr = YearRange("default.json")
    assert str(yr) == "default (default.json)"

    # Test single year (manually set since parser doesn't currently set it)
    yr = YearRange("some_file.json")
    yr.single_year = 2022
    assert str(yr) == "2022 (some_file.json)"

def test_edge_cases():
    """Test edge cases and special scenarios."""
    # Test with non-standard filename
    yr = YearRange("not-a-year-range.json")
    assert yr.start_year == 0
    assert yr.end_year == 9999

    # Test with empty filename
    yr = YearRange("")
    assert yr.start_year == 0
    assert yr.end_year == 9999

    # Test with invalid year range format but contains numbers
    yr = YearRange("data-2020.json")
    assert yr.start_year == 0
    assert yr.end_year == 9999

def test_contains_year_edge_cases():
    """Test edge cases for the contains_year method."""
    # Test with None values
    yr = YearRange("test.json")
    yr.start_year = None
    yr.end_year = None
    assert yr.contains_year(2022) is False

    # Test with equal start and end years
    yr = YearRange("2022-2022.json")
    assert yr.contains_year(2022) is True
    assert yr.contains_year(2021) is False
    assert yr.contains_year(2023) is False

if __name__ == "__main__":
    pytest.main([__file__])