from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Tuple
import json
import math

class ParameterType(Enum):
    SERVICE_21 = "21"
    SERVICE_22 = "22"

@dataclass(frozen=True)
class Parameter:
    type: ParameterType
    value: Union[int, str]

    @staticmethod
    def from_json(data: Dict) -> 'Parameter':
        for param_type in [ParameterType.SERVICE_21, ParameterType.SERVICE_22]:
            if param_type.value in data:
                # Handle both string and integer representations
                value = data[param_type.value]
                if isinstance(value, str):
                    value = int(value, 16)
                return Parameter(param_type, value)
        raise ValueError(f"Invalid parameter format: {data}")

    def as_message(self) -> str:
        if self.type == ParameterType.SERVICE_22:
            return f"{self.type.value}{self.value:04X}"
        else:
            return f"{self.type.value}{self.value:02X}"

class UnitCategory(Enum):
    TEMPERATURE = "temperature"
    LENGTH = "length"
    SPEED = "speed"
    REVOLUTIONS = "revolutions"
    DURATION = "duration"
    CURRENT = "current"
    CHARGE = "charge"
    VOLTAGE = "voltage"
    ENERGY = "energy"
    TORQUE = "torque"
    SCALAR = "scalar"
    PERCENT = "percent"
    NORMALIZED = "normalized"
    ENCODING = "encoding"
    BOOLEAN = "boolean"
    ANGLE = "angle"
    POWER = "power"
    PRESSURE = "pressure"
    VOLUME = "volume"
    MASS_FLOW = "massFlow"
    ACCELERATION = "acceleration"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class Scaling:
    bit_length: int
    max_value: float
    unit: str
    bit_offset: int = 0
    bytes_lsb: bool = False
    signed: bool = False
    min_value: float = 0
    offset: float = 0
    scalar: float = 1
    divisor: float = 1
    null_min: Optional[float] = None
    null_max: Optional[float] = None
    optimal_min: Optional[float] = None
    optimal_max: Optional[float] = None
    optimal_value: Optional[float] = None

    @staticmethod
    def from_json(data: Dict) -> 'Scaling':
        return Scaling(
            bit_offset=data.get('bix', 0),
            bit_length=data['len'],
            bytes_lsb=data.get('blsb', False),
            signed=data.get('sign', False),
            min_value=data.get('min', 0),
            max_value=data['max'],
            offset=data.get('add', 0),
            scalar=data.get('mul', 1),
            divisor=data.get('div', 1),
            unit=data['unit'],
            null_min=data.get('nullmin'),
            null_max=data.get('nullmax'),
            optimal_min=data.get('omin'),
            optimal_max=data.get('omax'),
            optimal_value=data.get('oval')
        )

    def decode_value(self, data: bytes) -> float:
        """Decode a value from bytes using the scaling parameters."""
        raw_value = self._extract_bits(data)
        if self.signed:
            raw_value = self._twos_complement(raw_value, self.bit_length)

        value = (raw_value * self.scalar / self.divisor) + self.offset

        if self.max_value > self.min_value:
            value = max(self.min_value, min(value, self.max_value))

        return value

    def _extract_bits(self, data: bytes) -> int:
        """Extract bits from byte data according to offset and length."""
        total_bits = len(data) * 8
        start_bit = self.bit_offset
        end_bit = start_bit + self.bit_length

        if end_bit > total_bits:
            raise ValueError(f"Not enough data: need {end_bit} bits, have {total_bits}")

        if self.bytes_lsb and self.bit_length > 8:
            # Reverse bytes for LSB format
            data = bytes(reversed(data))

        result = 0
        for i in range(start_bit, end_bit):
            byte_idx = i // 8
            bit_idx = 7 - (i % 8)  # MSB format
            if (data[byte_idx] & (1 << bit_idx)) != 0:
                result |= 1 << (end_bit - i - 1)

        return result

    def _twos_complement(self, value: int, bits: int) -> int:
        """Convert two's complement value to signed integer."""
        if value & (1 << (bits - 1)):
            value -= 1 << bits
        return value

@dataclass(frozen=True)
class EnumerationValue:
    value: str
    description: str

@dataclass(frozen=True)
class Enumeration:
    bit_length: int
    map: Dict[str, EnumerationValue]  # Changed from Dict[int, EnumerationValue]
    bit_offset: int = 0

    def __hash__(self) -> int:
        # Convert the map to a tuple of sorted items to make it hashable
        map_items = tuple(sorted(
            (k, hash(v))
            for k, v in self.map.items()
        ))
        return hash((self.bit_length, map_items, self.bit_offset))

    @staticmethod
    def from_json(data: Dict) -> 'Enumeration':
        value_map = {
            str(k): EnumerationValue(**v) if isinstance(v, dict) else EnumerationValue(str(v), str(v))
            for k, v in data['map'].items()
        }
        return Enumeration(
            bit_offset=data.get('bix', 0),
            bit_length=data['len'],
            map=value_map
        )

    def decode_value(self, data: bytes) -> str:
        """Decode an enumerated value from bytes."""
        # First extract the raw value as an integer
        raw_value = 0
        for i in range(self.bit_length):
            byte_idx = (self.bit_offset + i) // 8
            bit_idx = 7 - ((self.bit_offset + i) % 8)  # MSB format
            if byte_idx < len(data) and (data[byte_idx] & (1 << bit_idx)) != 0:
                raw_value |= 1 << (self.bit_length - i - 1)

        # Convert to string and look up in map
        str_value = str(raw_value)
        if str_value in self.map:
            return self.map[str_value].value
        return str_value  # Return raw value as string if no mapping exists

@dataclass(frozen=True)
class Signal:
    id: str
    name: str
    description: Optional[str]
    format: Union[Scaling, Enumeration]
    path: Optional[str] = None
    hidden: bool = False
    suggested_metric: Optional[str] = None

    @staticmethod
    def from_json(data: Dict) -> 'Signal':
        fmt = data['fmt']
        if 'map' in fmt:
            format_obj = Enumeration.from_json(fmt)
        else:
            format_obj = Scaling.from_json(fmt)

        return Signal(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            format=format_obj,
            path=data.get('path'),
            hidden=data.get('hidden', False),
            suggested_metric=data.get('suggestedMetric')
        )

@dataclass(frozen=True)
class Command:
    parameter: Parameter
    header: int
    receive_address: Optional[int]
    signals: Tuple[Signal, ...]  # Using tuple instead of set for hashability
    update_frequency: float
    extended_address: Optional[int] = None
    tester_address: Optional[int] = None
    timeout: Optional[int] = None
    force_flow_control: bool = False
    debug: bool = False

    @staticmethod
    def from_json(data: Dict) -> 'Command':
        header = int(data['hdr'], 16)
        receive_address = int(data['rax'], 16) if 'rax' in data else None
        signals = tuple(sorted(
            (Signal.from_json(s) for s in data['signals']),
            key=lambda x: x.id
        ))

        return Command(
            parameter=Parameter.from_json(data['cmd']),
            header=header,
            receive_address=receive_address,
            signals=signals,
            update_frequency=data['freq'],
            extended_address=int(data['eax'], 16) if 'eax' in data else None,
            tester_address=int(data['tst'], 16) if 'tst' in data else None,
            timeout=int(data['tmo'], 16) if 'tmo' in data else None,
            force_flow_control=data.get('fcm1', False),
            debug=data.get('dbg', False)
        )

@dataclass
class SignalSet:
    commands: Set[Command]
    diagnostic_level: Optional[int] = None
    signal_groups: Optional[Set] = None

    @classmethod
    def from_json(cls, json_data: str) -> 'SignalSet':
        data = json.loads(json_data)
        commands = {Command.from_json(cmd) for cmd in data['commands']}
        diagnostic_level = int(data['diagnosticLevel'], 16) if 'diagnosticLevel' in data else None

        return cls(
            commands=commands,
            diagnostic_level=diagnostic_level,
            signal_groups=None  # TODO: Implement signal groups if needed
        )
