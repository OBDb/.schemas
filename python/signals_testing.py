import pytest
from typing import Dict, Any, Optional
from can_frame import CANIDFormat
from command_registry import decode_obd_response
from signals import SignalSet, Command, Signal, Scaling

def obd_testrunner(
        signalset_json: str,
        response_hex: str,
        expected_values: Dict[str, float],
        can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled: Optional[bool] = None
    ):
    """Test decoding an OBD response against expected values.

    Args:
        signalset_json: JSON string containing the signal set definition
        response_hex: Hex string of the OBD response
        expected_values: Dictionary mapping signal IDs to their expected values
    """
    signalset = SignalSet.from_json(signalset_json)
    actual_values = decode_obd_response(
        signalset,
        response_hex,
        can_id_format=can_id_format,
        extended_addressing_enabled=extended_addressing_enabled
    )

    # Test each expected signal value
    for signal_id, expected_value in expected_values.items():
        assert signal_id in actual_values, f"Signal {signal_id} not found in decoded response"
        actual_value = actual_values[signal_id]
        assert pytest.approx(actual_value) == expected_value, \
            f"Signal {signal_id} value mismatch: got {actual_value}, expected {expected_value}"
