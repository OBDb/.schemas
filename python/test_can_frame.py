import pytest
from .can_frame import (
    CANFrame, CANFrameScanner, CANIDFormat, CANFrameError,
    DataFrameType, DataFrameHeader
)

def test_single_frame():
    """Test parsing a single frame response."""
    response = "7E803410D00"  # Standard single frame response
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )

    assert scanner is not None
    packet = next(scanner)
    assert packet.can_identifier == "7E8"
    assert packet.extended_receive_address is None
    assert packet.data == bytes.fromhex("410D00")

def test_multi_frame():
    """Test parsing a multi-frame response."""
    response = """
    7E81014490201534231
    7E8215A53334A453630
    7E82245323832313032
    """
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )

    assert scanner is not None
    packet = next(scanner)
    assert packet.can_identifier == "7E8"
    assert len(packet.data) == 20
    assert packet.data == bytes.fromhex("4902015342315A53334A45363045323832313032")

def test_extended_addressing():
    """Test parsing responses with extended addressing."""
    response = "7E8F103410D00"
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled=True
    )

    assert scanner is not None
    packet = next(scanner)
    assert packet.can_identifier == "7E8"
    assert packet.extended_receive_address == "F1"
    assert packet.data == bytes.fromhex("410D00")

def test_malformed_frames():
    """Test handling of malformed frame data."""
    # Test invalid CAN identifier
    with pytest.raises(CANFrameError):
        CANFrame.from_line(
            "ZZZ064B000000000",  # Invalid hex
            can_id_format=CANIDFormat.ELEVEN_BIT
        )

    # Test truncated frame
    with pytest.raises(CANFrameError):
        CANFrame.from_line(
            "7E8",  # Too short
            can_id_format=CANIDFormat.ELEVEN_BIT
        )

    # Test invalid frame type
    with pytest.raises(CANFrameError):
        CANFrame.from_line(
            "7E8F64B000000000",  # Invalid frame type (F)
            can_id_format=CANIDFormat.ELEVEN_BIT
        )

def test_can_id_formats():
    """Test different CAN ID format handling."""
    # Test 11-bit format with extended addressing
    frame = CANFrame.from_line(
        "7E8F103410D00",
        can_id_format=CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled=True
    )
    assert frame.can_identifier == "7E8"

    # Test 29-bit format.
    frame = CANFrame.from_line(
        """
        18DAF126103B6260010000FF
        18DAF1262100F000000000D9
        18DAF1262200E800DA00E300
        18DAF1262300000000000000
        18DAF126241720161A000000
        18DAF1262500000000000000
        18DAF1262600000000000000
        18DAF1262700000000000000
        18DAF1262800000000555555
        """,
        can_id_format=CANIDFormat.TWENTY_NINE_BIT
    )
    assert frame.can_identifier == "18DAF126"

if __name__ == "__main__":
    pytest.main([__file__])
