import pytest
from typing import Optional, Set

from .signals import Filter


@pytest.mark.parametrize(
    "filter_params, model_year, expected",
    [
        # Test case 1: from < to, model_year within range
        ({"from_year": 2000, "to_year": 2010}, 2005, True),
        # Test case 2: from < to, model_year equals from_year
        ({"from_year": 2000, "to_year": 2010}, 2000, True),
        # Test case 3: from < to, model_year equals to_year
        ({"from_year": 2000, "to_year": 2010}, 2010, True),
        # Test case 4: from < to, model_year outside range (less)
        ({"from_year": 2000, "to_year": 2010}, 1999, False),
        # Test case 5: from < to, model_year outside range (greater)
        ({"from_year": 2000, "to_year": 2010}, 2011, False),

        # Test case 6: from > to, model_year >= from_year
        ({"from_year": 2010, "to_year": 2000}, 2015, True),
        # Test case 7: from > to, model_year equals from_year
        ({"from_year": 2010, "to_year": 2000}, 2010, True),
        # Test case 8: from > to, model_year <= to_year
        ({"from_year": 2010, "to_year": 2000}, 1995, True),
        # Test case 9: from > to, model_year equals to_year
        ({"from_year": 2010, "to_year": 2000}, 2000, True),
        # Test case 10: from > to, model_year between to_year and from_year (exclusive)
        ({"from_year": 2010, "to_year": 2000}, 2005, False),

        # Test case 11: only from_year, model_year >= from_year
        ({"from_year": 2000}, 2005, True),
        # Test case 12: only from_year, model_year equals from_year
        ({"from_year": 2000}, 2000, True),
        # Test case 13: only from_year, model_year < from_year
        ({"from_year": 2000}, 1999, False),

        # Test case 14: only to_year, model_year <= to_year
        ({"to_year": 2010}, 2005, True),
        # Test case 15: only to_year, model_year equals to_year
        ({"to_year": 2010}, 2010, True),
        # Test case 16: only to_year, model_year > to_year
        ({"to_year": 2010}, 2011, False),

        # Test case 17: only years, model_year in years
        ({"years": {2000, 2005, 2010}}, 2005, True),
        # Test case 18: only years, model_year not in years
        ({"years": {2000, 2005, 2010}}, 2003, False),
        # Test case 19: only years, empty set
        ({"years": set()}, 2005, False),

        # Test case 20: from < to AND years, model_year in range, not in years
        ({"from_year": 2000, "to_year": 2010, "years": {2015}}, 2005, True),
        # Test case 21: from < to AND years, model_year not in range, in years
        ({"from_year": 2000, "to_year": 2010, "years": {2015}}, 2015, True),
        # Test case 22: from < to AND years, model_year in range AND in years
        ({"from_year": 2000, "to_year": 2010, "years": {2005}}, 2005, True),
        # Test case 23: from < to AND years, model_year not in range AND not in years
        ({"from_year": 2000, "to_year": 2010, "years": {2015}}, 2012, False),

        # Test case 24: No filter properties, model_year provided
        ({}, 2005, False),
        # Test case 25: No filter properties, model_year is None
        ({}, None, False),
        # Test case 26: Filter properties exist, model_year is None
        ({"from_year": 2000}, None, False),

        # Test case 27: from_json with all fields
        (Filter.from_json({"from": 2000, "to": 2010, "years": [2005, 2015]}), 2005, True),
        # Test case 28: from_json with only from
        (Filter.from_json({"from": 2000}), 2000, True),
        # Test case 29: from_json with only to
        (Filter.from_json({"to": 2010}), 2010, True),
        # Test case 30: from_json with only years
        (Filter.from_json({"years": [2005, 2015]}), 2015, True),
        # Test case 31: from_json with empty dict
        (Filter.from_json({}), 2005, False),
    ],
)
def test_filter_matches(filter_params, model_year: Optional[int], expected: bool):
    if isinstance(filter_params, Filter): # Already a Filter instance from from_json tests
        test_filter = filter_params
    else:
        test_filter = Filter(
            from_year=filter_params.get("from_year"),
            to_year=filter_params.get("to_year"),
            years=filter_params.get("years"),
        )
    assert test_filter.matches(model_year) == expected

def test_filter_from_json_empty_years():
    f = Filter.from_json({"years": []})
    assert f.years == None
    assert not f.matches(2000)

def test_filter_from_json_none_values():
    f = Filter.from_json({"from": None, "to": None, "years": None})
    assert f.from_year is None
    assert f.to_year is None
    assert f.years is None
    assert not f.matches(2000)

def test_filter_from_json_partial_none_values():
    f = Filter.from_json({"from": 2000, "to": None, "years": [2005]})
    assert f.from_year == 2000
    assert f.to_year is None
    assert f.years == {2005}
    assert f.matches(2000)
    assert f.matches(2005)
    assert not f.matches(1999)
    assert f.matches(2001)
