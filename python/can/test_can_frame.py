import pytest
from pathlib import Path
import sys

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from can.can_frame import (
    CANFrame, CANFrameScanner, CANIDFormat, CANFrameError,
    DataFrameType, DataFrameHeader, CANFramePart, CANPacket
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

def test_empty_input():
    """Test handling of empty input string."""
    response = ""
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )
    assert scanner is not None
    assert len(scanner.frames) == 0
    with pytest.raises(StopIteration):
        next(scanner)

def test_data_frame_type_conversion():
    """Test DataFrameType conversions from raw bytes."""
    assert DataFrameType.from_byte(0x00) == DataFrameType.SINGLE_FRAME
    assert DataFrameType.from_byte(0x01) == DataFrameType.FIRST_FRAME
    assert DataFrameType.from_byte(0x02) == DataFrameType.CONSECUTIVE_FRAME
    assert DataFrameType.from_byte(0x03) == DataFrameType.FLOW_CONTROL_FRAME

    # Test invalid frame type
    with pytest.raises(CANFrameError):
        DataFrameType.from_byte(0x04)  # Invalid type

def test_first_frame_parsing():
    """Test parsing of a first frame in a multi-frame message."""
    frame = CANFrame.from_line(
        "7E81014490201534231",
        can_id_format=CANIDFormat.ELEVEN_BIT
    )
    assert frame.data_frame_type == DataFrameType.FIRST_FRAME
    assert frame.data_frame_header.type == DataFrameHeader.Type.FIRST
    assert frame.data_frame_header.value == 20
    # Use the exact bytes from the actual data
    assert frame.data == bytes([0x49, 0x02, 0x01, 0x53, 0x42, 0x31])

def test_consecutive_frame_parsing():
    """Test parsing of a consecutive frame in a multi-frame message."""
    frame = CANFrame.from_line(
        "7E8215A53334A453630",
        can_id_format=CANIDFormat.ELEVEN_BIT
    )
    assert frame.data_frame_type == DataFrameType.CONSECUTIVE_FRAME
    assert frame.data_frame_header.type == DataFrameHeader.Type.CONSECUTIVE
    assert frame.data_frame_header.value == 0x1  # Frame index
    assert frame.data == bytes.fromhex("5A53334A453630")

def test_flow_control_frame():
    """Test parsing of a flow control frame."""
    frame = CANFrame.from_line(
        "7E8300112233",
        can_id_format=CANIDFormat.ELEVEN_BIT
    )
    assert frame.data_frame_type == DataFrameType.FLOW_CONTROL_FRAME
    assert frame.data_frame_header.type == DataFrameHeader.Type.FLOW
    assert frame.data == bytes.fromhex("00112233")

def test_multi_frame_with_flow_control():
    """Test parsing a response with flow control frame."""
    response = """
    7E81014490201534231
    7DF3010000000000
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
    # Flow control frame should be ignored

def test_partial_multi_frame():
    """Test handling of incomplete multi-frame messages."""
    # Only first frame is present, consecutive frames missing
    response = "7E81014490201534231"
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )

    assert scanner is not None
    with pytest.raises(StopIteration):
        next(scanner)

def test_malformed_frame_parts():
    """Test specific error cases for each frame part."""
    # Malformed identifier (11-bit)
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.IDENTIFIER

    # Malformed identifier (29-bit)
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("18DAF", can_id_format=CANIDFormat.TWENTY_NINE_BIT)
    assert excinfo.value.part == CANFramePart.IDENTIFIER

    # Malformed extended address
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E8", can_id_format=CANIDFormat.ELEVEN_BIT, extended_addressing_enabled=True)
    assert excinfo.value.part == CANFramePart.EXTENDED_RECEIVE_ADDRESS

    # Malformed type
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E8", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.TYPE

    # Malformed single frame size
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E80", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.SIZE

    # Malformed first frame size
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E81", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.SIZE

    # Malformed consecutive frame index
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E82", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.INDEX

    # Malformed data (empty)
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E803", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.DATA

    # Malformed data (odd length)
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E8034", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.DATA

    # Invalid hex data
    with pytest.raises(CANFrameError) as excinfo:
        CANFrame.from_line("7E8034ZZ", can_id_format=CANIDFormat.ELEVEN_BIT)
    assert excinfo.value.part == CANFramePart.DATA

def test_whitespace_handling():
    """Test that whitespace is correctly handled."""
    # Test with spaces between characters
    response = "7 E 8 0 3 4 1 0 D 0 0"
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )

    assert scanner is not None
    packet = next(scanner)
    assert packet.can_identifier == "7E8"
    assert packet.data == bytes.fromhex("410D00")

    # Test with newlines and tabs - need to pass a valid CAN frame
    response = """
    7E8034100
    """
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )

    assert scanner is not None
    packet = next(scanner)
    assert packet.can_identifier == "7E8"
    assert packet.data == bytes.fromhex("4100")

def test_multiple_packets():
    """Test processing multiple complete packets."""
    response = """
    7E80341AAAA
    7E80342BBBB
    7E80343CCCC
    """
    scanner = CANFrameScanner.from_ascii_string(
        response,
        can_id_format=CANIDFormat.ELEVEN_BIT
    )

    assert scanner is not None

    # First packet
    packet1 = next(scanner)
    assert packet1.can_identifier == "7E8"
    assert packet1.data == bytes.fromhex("41AAAA")

    # Second packet
    packet2 = next(scanner)
    assert packet2.can_identifier == "7E8"
    assert packet2.data == bytes.fromhex("42BBBB")

    # Third packet
    packet3 = next(scanner)
    assert packet3.can_identifier == "7E8"
    assert packet3.data == bytes.fromhex("43CCCC")

    # No more packets
    with pytest.raises(StopIteration):
        next(scanner)

def test_direct_packet_creation():
    """Test direct creation of CANPacket objects."""
    packet = CANPacket(
        can_identifier="7E8",
        extended_receive_address="F1",
        data=bytes.fromhex("410D00")
    )

    assert packet.can_identifier == "7E8"
    assert packet.extended_receive_address == "F1"
    assert packet.data == bytes.fromhex("410D00")

if __name__ == "__main__":
    pytest.main([__file__])