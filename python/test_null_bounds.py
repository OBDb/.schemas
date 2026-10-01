import pytest

from can.signals import Scaling


def scaling(**fields) -> Scaling:
    return Scaling.from_json({"len": 8, "max": 255, "unit": "scalar", **fields})


@pytest.mark.parametrize("fields, data, value", [
    # A reply at or past a null bound decodes to no value, as the app shows it.
    ({"nullmax": 255}, b"\xff", None),
    ({"nullmax": 250}, b"\xfb", None),
    ({"nullmin": 0}, b"\x00", None),
    ({"min": -40, "add": -40, "nullmin": -40}, b"\x00", None),
    # Inside the bounds the value decodes as before.
    ({"nullmax": 255}, b"\xfe", 254),
    ({"nullmin": 0}, b"\x01", 1),
    ({}, b"\xff", 255),
])
def test_null_bounds_decode_to_none(fields, data, value):
    assert scaling(**fields).decode_value(data) == value
