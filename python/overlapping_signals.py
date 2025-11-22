"""
Overlapping signals validation for signalset files.

This module has minimal dependencies (only json from stdlib) so it can be
used by the CLI without requiring pytest, yaml, or other test dependencies.
"""
import json
from typing import Dict, List, Any


class OverlappingSignalError(Exception):
    """Raised when signals within a command have overlapping bit definitions."""
    pass


def check_overlapping_signals_no_raise(signalset_json: str) -> List[Dict[str, Any]]:
    """
    Check a signalset for overlapping signal bit definitions within commands.

    Uses a bitset approach: for each command, track which bits are occupied.
    If a signal tries to use a bit that's already occupied, it's an overlap.

    Args:
        signalset_json: JSON string containing the signal set definition

    Returns:
        List of overlap errors, each containing:
        - command: command identifier (hdr/cmd)
        - signal_id: the signal that caused the overlap
        - bit: the bit index that was already occupied
        - conflicting_signal_id: the signal that already occupied the bit
    """
    signalset = json.loads(signalset_json)

    errors = []

    for command in signalset.get('commands', []):
        # Track which bits are occupied and by which signal
        occupied_bits: Dict[int, str] = {}

        cmd_identifier = f"hdr={command.get('hdr', '?')}, cmd={command.get('cmd', '?')}"

        for signal in command.get('signals', []):
            signal_id = signal.get('id', 'unknown')
            fmt = signal.get('fmt', {})

            start_bit = fmt.get('bix', 0)
            bit_length = fmt.get('len', 0)

            for bit in range(start_bit, start_bit + bit_length):
                if bit in occupied_bits:
                    errors.append({
                        'command': cmd_identifier,
                        'signal_id': signal_id,
                        'bit': bit,
                        'conflicting_signal_id': occupied_bits[bit]
                    })
                    # Only report the first conflicting bit per signal
                    break
                occupied_bits[bit] = signal_id

    return errors


def check_overlapping_signals(signalset_json: str) -> List[Dict[str, Any]]:
    """
    Check a signalset for overlapping signal bit definitions within commands.

    Args:
        signalset_json: JSON string containing the signal set definition

    Returns:
        Empty list if no overlaps found

    Raises:
        OverlappingSignalError: If any overlapping signals are found
    """
    errors = check_overlapping_signals_no_raise(signalset_json)

    if errors:
        error_messages = []
        for err in errors:
            error_messages.append(
                f"Signal '{err['signal_id']}' overlaps with '{err['conflicting_signal_id']}' "
                f"at bit {err['bit']} in command [{err['command']}]"
            )
        raise OverlappingSignalError(
            f"Found {len(errors)} overlapping signal(s):\n" + "\n".join(error_messages)
        )

    return errors


def test_no_overlapping_signals(signalset_json: str):
    """
    Test that a signalset has no overlapping signal bit definitions.

    This function can be used by other repos to validate their signalset files.

    Args:
        signalset_json: JSON string containing the signal set definition

    Raises:
        OverlappingSignalError: If any overlapping signals are found
    """
    check_overlapping_signals(signalset_json)
