from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Iterator
import re

class CANFramePart(Enum):
    """Identifies different segments of a CAN frame for error reporting."""
    IDENTIFIER = auto()
    EXTENDED_RECEIVE_ADDRESS = auto()
    TYPE = auto()
    SIZE = auto()
    INDEX = auto()
    DATA = auto()

class CANFrameError(Exception):
    """
    Raised when parsing CAN frames fails. Includes details about which part
    of the frame caused the error to aid in debugging.
    """
    def __init__(self, message: str, source: str = "", part: Optional[CANFramePart] = None):
        self.message = message
        self.source = source  # Original problematic frame data
        self.part = part      # Which part of the frame had issues
        super().__init__(self.message)

class CANIDFormat(Enum):
    """
    CAN ID formats used in automotive networks:
    ELEVEN_BIT: Standard format (11-bit identifier)
    TWENTY_NINE_BIT: Extended format (29-bit identifier)
    """
    ELEVEN_BIT = auto()
    TWENTY_NINE_BIT = auto()

class DataFrameType(Enum):
    """
    ISO-TP frame types used for segmented message transfer:
    SINGLE_FRAME: Complete message in one frame
    FIRST_FRAME: Initial frame of multi-frame message
    CONSECUTIVE_FRAME: Continuation frame in multi-frame message
    FLOW_CONTROL_FRAME: Flow control management
    """
    SINGLE_FRAME = 0x00
    FIRST_FRAME = 0x01
    CONSECUTIVE_FRAME = 0x02
    FLOW_CONTROL_FRAME = 0x03

    @classmethod
    def from_byte(cls, byte: int) -> 'DataFrameType':
        """Converts raw frame type byte to enum, handling invalid types."""
        try:
            return cls(byte)
        except ValueError:
            raise CANFrameError(f"Invalid data frame type: {byte:02X}")

@dataclass
class DataFrameHeader:
    """
    ISO-TP frame header information. Contains either:
    - Message size (for SINGLE/FIRST frames)
    - Frame sequence number (for CONSECUTIVE frames)
    """
    class Type(Enum):
        SINGLE = auto()      # Complete message
        FIRST = auto()       # Start of segmented message
        CONSECUTIVE = auto() # Continuation of segmented message
        FLOW = auto()        # Flow control

    type: Type
    value: Optional[int] = None  # Size or sequence number

@dataclass
class CANFrame:
    """Represents a single CAN frame with ISO-TP transport layer information."""
    can_id_format: CANIDFormat
    can_identifier: str
    extended_receive_address: Optional[str]
    data_frame_type: DataFrameType
    data_frame_header: DataFrameHeader
    data: bytes

    @staticmethod
    def parse_can_identifier(line: str, can_id_format: CANIDFormat) -> Tuple[str, int]:
        """
        Extracts CAN identifier from raw frame data.
        Returns tuple of (identifier, index after identifier).

        11-bit IDs use 3 hex chars, 29-bit use 8 hex chars.
        """
        if can_id_format == CANIDFormat.ELEVEN_BIT:
            if len(line) < 3:
                raise CANFrameError("Malformed CAN identifier", line, CANFramePart.IDENTIFIER)
            return line[:3], 3
        elif can_id_format == CANIDFormat.TWENTY_NINE_BIT:
            if len(line) < 8:
                raise CANFrameError("Malformed CAN identifier", line, CANFramePart.IDENTIFIER)
            return line[:8], 8

    @classmethod
    def from_line(cls, line: str, can_id_format: CANIDFormat, extended_addressing_enabled: bool = False) -> 'CANFrame':
        """
        Parses a single line of CAN frame data. Handles:
        - Standard and extended CAN IDs
        - ISO-TP segmentation
        - Optional extended addressing
        """
        # Remove any whitespace
        line = re.sub(r'\s+', '', line)

        # Parse CAN identifier
        can_identifier, index = cls.parse_can_identifier(line, can_id_format)

        # Parse extended addressing or type
        extended_receive_address = None

        if extended_addressing_enabled is True:
            if len(line) < index + 2:
                raise CANFrameError("Malformed extended receive address", line, CANFramePart.EXTENDED_RECEIVE_ADDRESS)
            extended_receive_address = line[index:index + 2]
            index += 2

        # Parse type
        if len(line) < index + 1:
            raise CANFrameError("Malformed type", line, CANFramePart.TYPE)
        try:
            byte = int(line[index], 16)
            data_frame_type = DataFrameType.from_byte(byte)
            index += 1
        except ValueError:
            raise CANFrameError(f"Invalid character: {line[index]}")

        # Parse frame header based on type
        data_frame_header = None
        if data_frame_type == DataFrameType.SINGLE_FRAME:
            if len(line) < index + 1:
                raise CANFrameError("Malformed size", line, CANFramePart.SIZE)
            try:
                size = int(line[index], 16)
                data_frame_header = DataFrameHeader(DataFrameHeader.Type.SINGLE, size)
                index += 1
            except ValueError:
                raise CANFrameError("Invalid size")

        elif data_frame_type == DataFrameType.FIRST_FRAME:
            if len(line) < index + 3:
                raise CANFrameError("Malformed size", line, CANFramePart.SIZE)
            try:
                size = int(line[index:index + 3], 16)
                data_frame_header = DataFrameHeader(DataFrameHeader.Type.FIRST, size)
                index += 3
            except ValueError:
                raise CANFrameError("Invalid size")

        elif data_frame_type == DataFrameType.CONSECUTIVE_FRAME:
            if len(line) < index + 1:
                raise CANFrameError("Malformed index", line, CANFramePart.INDEX)
            try:
                frame_index = int(line[index], 16)
                data_frame_header = DataFrameHeader(DataFrameHeader.Type.CONSECUTIVE, frame_index)
                index += 1
            except ValueError:
                raise CANFrameError("Invalid frame index")

        elif data_frame_type == DataFrameType.FLOW_CONTROL_FRAME:
            data_frame_header = DataFrameHeader(DataFrameHeader.Type.FLOW)

        # Parse remaining data
        if len(line) <= index:
            raise CANFrameError("Malformed data", line, CANFramePart.DATA)
        data_string = line[index:]
        if len(data_string) % 2 != 0:
            raise CANFrameError("Malformed data (odd length)", line, CANFramePart.DATA)
        try:
            data = bytes.fromhex(data_string)
        except ValueError:
            raise CANFrameError("Invalid hex data", line, CANFramePart.DATA)

        return cls(
            can_id_format=can_id_format,
            can_identifier=can_identifier,
            extended_receive_address=extended_receive_address,
            data_frame_type=data_frame_type,
            data_frame_header=data_frame_header,
            data=data
        )

@dataclass
class CANPacket:
    """
    Complete ISO-TP message reassembled from one or more CAN frames.
    Contains the original CAN ID and complete payload data.
    """
    can_identifier: str
    extended_receive_address: Optional[str]
    data: bytes

class CANFrameScanner:
    """
    Processes CAN frames and reassembles them into complete ISO-TP packets.
    Handles multi-frame messages by maintaining partial packet state.
    """
    def __init__(self, frames: List[CANFrame]):
        self.frames = frames
        self._partial_packets: Dict[str, Tuple[bytes, int]] = {}  # CAN ID -> (accumulated data, total size)
        self._frame_index = 0

    @classmethod
    def from_ascii_string(cls, ascii_string: str,
                         can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
                         extended_addressing_enabled: Optional[bool] = None) -> Optional['CANFrameScanner']:
        """
        Creates a scanner from ASCII hex dump of CAN frames.
        Handles both single-line and multi-line inputs.
        """
        lines = cls._format_ascii_string(ascii_string)
        if not lines:
            return None

        frames = []
        for line in lines:
            try:
                frame = CANFrame.from_line(line, can_id_format, extended_addressing_enabled)
                frames.append(frame)
            except CANFrameError as e:
                print(f"Error parsing frame: {e}")
                continue

        return cls(frames)

    @staticmethod
    def _format_ascii_string(ascii_string: str) -> Optional[List[str]]:
        """Splits and cleans up raw ASCII input into frame strings."""
        return [line.strip() for line in ascii_string.split('\n')]

    def __iter__(self) -> Iterator[CANPacket]:
        return self

    def __next__(self) -> CANPacket:
        """
        Processes frames sequentially, yielding complete packets.
        Maintains state for multi-frame messages until they're complete.
        """
        while self._frame_index < len(self.frames):
            frame = self.frames[self._frame_index]
            self._frame_index += 1

            can_id = frame.can_identifier

            if frame.data_frame_header.type == DataFrameHeader.Type.SINGLE:
                return CANPacket(
                    can_identifier=can_id,
                    extended_receive_address=frame.extended_receive_address,
                    data=frame.data
                )

            elif frame.data_frame_header.type == DataFrameHeader.Type.FIRST:
                self._partial_packets[can_id] = (frame.data, frame.data_frame_header.value)

            elif frame.data_frame_header.type == DataFrameHeader.Type.CONSECUTIVE:
                if can_id not in self._partial_packets:
                    continue

                accumulator, packet_size = self._partial_packets[can_id]
                accumulator += frame.data

                if len(accumulator) >= packet_size:
                    data = accumulator[:packet_size]
                    del self._partial_packets[can_id]
                    return CANPacket(
                        can_identifier=can_id,
                        extended_receive_address=frame.extended_receive_address,
                        data=data
                    )
                else:
                    self._partial_packets[can_id] = (accumulator, packet_size)

            elif frame.data_frame_header.type == DataFrameHeader.Type.FLOW:
                continue  # Flow control frames not needed for reassembly

        raise StopIteration
