import os
import pytest
from pathlib import Path

from json_formatter import format_file
from signals_testing import check_overlapping_signals, OverlappingSignalError

TESTDATA_DIR = os.path.join(Path(__file__).parent, 'testdata')


def test_overlapping_signals_rejected_by_format_file():
    """Test that format_file raises OverlappingSignalError for bad-overlappingsignals.json."""
    bad_file = os.path.join(TESTDATA_DIR, 'bad-overlappingsignals.json')

    with pytest.raises(OverlappingSignalError) as exc_info:
        format_file(bad_file)

    error_message = str(exc_info.value)
    assert "F150_ODO_2" in error_message
    assert "F150_ODO" in error_message


def test_overlapping_signals_detected():
    """Test that overlapping signals in bad-overlappingsignals.json are detected."""
    bad_file = os.path.join(TESTDATA_DIR, 'bad-overlappingsignals.json')
    with open(bad_file) as f:
        signalset_json = f.read()

    with pytest.raises(OverlappingSignalError) as exc_info:
        check_overlapping_signals(signalset_json)

    # Verify the error message contains the expected signal IDs
    error_message = str(exc_info.value)
    assert "F150_ODO_2" in error_message
    assert "F150_ODO" in error_message


def test_non_overlapping_signals_pass():
    """Test that non-overlapping signals pass validation."""
    signalset_json = '''{
        "commands": [{
            "hdr": "720", "rax": "728", "cmd": {"22": "404C"}, "freq": 5,
            "signals": [
                {"id": "SIG_A", "fmt": {"bix": 0, "len": 8}},
                {"id": "SIG_B", "fmt": {"bix": 8, "len": 8}},
                {"id": "SIG_C", "fmt": {"bix": 16, "len": 16}}
            ]
        }]
    }'''
    # Should not raise
    check_overlapping_signals(signalset_json)


def test_overlapping_signals_with_implicit_bix():
    """Test that implicit bix=0 is handled correctly for overlap detection."""
    signalset_json = '''{
        "commands": [{
            "hdr": "720", "rax": "728", "cmd": {"22": "404C"}, "freq": 5,
            "signals": [
                {"id": "SIG_A", "fmt": {"len": 8}},
                {"id": "SIG_B", "fmt": {"len": 4}}
            ]
        }]
    }'''
    with pytest.raises(OverlappingSignalError) as exc_info:
        check_overlapping_signals(signalset_json)

    error_message = str(exc_info.value)
    assert "SIG_B" in error_message
    assert "SIG_A" in error_message
