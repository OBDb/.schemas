import pytest
import os

from .signals_testing import obd_testrunner

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))

TEST_CASES = [
    # 2024 model years
    # Gear
    ("7E804621E1203", {"F150_GEAR": "3"}),

    # 2021 model year
    # Target vehicle speed - -61.2 km/h
    ("76C0562A224FF56", {"F150_CC_TGT_VSS": -61.2}),

    # 2019 model year
    # Tire pressures
    ("72E05622813028C", {"F150_TP_FL": 32.6}),
    ("72E056228140273", {"F150_TP_FR": 31.35}),
    ("72E056228150291", {"F150_TP_RRO": 32.85}),
    ("72E05622816026E", {"F150_TP_RLO": 31.1}),
    ("72E056228170000", {"F150_TP_RRI": 0.0}),
    ("72E056228180000", {"F150_TP_RLI": 0.0}),

    # 2012 model year
    # Odometer - 234652.4 km
    ("7280662404C23CE1C", {"F150_ODO": 234652.4}),
    # Fuel level - 49.02%
    ("7E80462F42F7D", {"F150_FLI": 49.01960784313726}),
    # Steering angle - 555.7 degrees
    ("76805623201AB6A", {"F150_STEER_ANGLE": 555.6999999999998}),
    # Transmission oil temp - 68.31 C
    ("7E805621E1C0445", {"F150_TOT": 68.3125}),
]

def test_ford_f150_signals():
    """Test Ford F-150 signal decoding against known responses."""
    signalset_path = os.path.join(REPO_ROOT, 'testdata', 'ford-f-150.json')
    with open(signalset_path) as f:
        signalset_json = f.read()

    # Run each test case
    for response_hex, expected_values in TEST_CASES:
        try:
            obd_testrunner(signalset_json, response_hex, expected_values)
        except Exception as e:
            pytest.fail(f"Failed on response {response_hex}: {e}")

if __name__ == '__main__':
    test_ford_f150_signals()
