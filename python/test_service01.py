import os
from pathlib import Path
import pytest
import sys

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from can.can_frame import CANIDFormat
from .signals_testing import obd_testrunner

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))

TEST_CASES = [
            ("""
18DAF1601039627028F8F000
18DAF1602100000004040100
18DAF1602200000000004E00
18DAF160234C000000000000
18DAF1602400000000000000
18DAF1602500000000000000
18DAF1602600000000000000
18DAF1602700000000000000
18DAF1602800005555555555
""", {"CIVIC_AAT": 36}),
            ("""
18DAF1601039627028F8F000
18DAF1602100000004070101
18DAF1602200000000005800
18DAF1602357000000000000
18DAF1602400000000000000
18DAF1602500000000000000
18DAF1602600000000000000
18DAF1602700000000000000
18DAF1602800005555555555
""", {"CIVIC_AAT": 47}),

            # ODO + runtime
            ("""
18DAF1101039622660801FFF
18DAF11021F3FFF000000000
18DAF1102200000000000000
18DAF1102300002CD11B0201
18DAF1102400040040408300
18DAF1102501021D000005BD
18DAF110260150017035018F
18DAF110278500E500460000
18DAF1102800005555555555
""", {
    "CIVIC_ODO": 102277.0,
    "CIVIC_RUNTM": 229,
    }),
            ("""
18DAF1101039622660801FFF
18DAF11021F3FFF000000000
18DAF1102200000000000000
18DAF1102300002CFC1B0101
18DAF1102400040040408300
18DAF1102501021100000947
18DAF11026040504FD4B018F
18DAF11027B3063B02F00000
18DAF1102800005555555555
""", {
    "CIVIC_ODO": 102323.0,
    "CIVIC_RUNTM": 1595,
    }),
]

def test_service01_signals():
    """Test Service 01 decoding."""
    signalset_path = os.path.join(REPO_ROOT, 'testdata', 'service-01.json')
    with open(signalset_path) as f:
        signalset_json = f.read()

    # Run each test case
    for response_hex, expected_values in TEST_CASES:
        try:
            obd_testrunner(signalset_json, response_hex, expected_values, can_id_format=CANIDFormat.TWENTY_NINE_BIT)
        except Exception as e:
            pytest.fail(f"Failed on response {response_hex}: {e}")


if __name__ == '__main__':
    pytest.main([__file__])
