from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum

from .can_frame import CANFrame, CANPacket, CANFrameScanner, CANIDFormat
from .signals import Command, Enumeration, Scaling, SignalSet

class ServiceType(Enum):
    SERVICE_21 = 0x21
    SERVICE_22 = 0x22

@dataclass
class CommandResponse:
    command: 'Command'
    data: bytes
    values: Dict[str, Any]

class CommandRegistry:
    def __init__(self, commands: List['Command']):
        # Group commands by parameter for efficient lookup
        self.commands_by_parameter = {}
        for cmd in commands:
            # Cast cmd.parameter.type.value from a hex string to an integer
            service_id = int(cmd.parameter.type.value, 16)
            param_key = (service_id, cmd.parameter.value)
            if param_key not in self.commands_by_parameter:
                self.commands_by_parameter[param_key] = []
            self.commands_by_parameter[param_key].append(cmd)

    def identify_commands(self, packet: 'CANPacket') -> List[CommandResponse]:
        """Identify and parse commands from a CAN packet."""
        data = packet.data
        if not data:
            return []

        # First byte should be service response (service ID + 0x40)
        service_response = data[0]
        if service_response < 0x40:
            return []

        service = service_response - 0x40
        data = data[1:]  # Remove service byte

        if service == ServiceType.SERVICE_21.value:
            return self._extract_service_21_commands(packet.can_identifier, data)
        elif service == ServiceType.SERVICE_22.value:
            return self._extract_service_22_commands(packet.can_identifier, data)
        return []

    def _extract_service_22_commands(self, can_id: str, data: bytes) -> List[CommandResponse]:
        responses = []
        while data:
            if len(data) < 2:
                break

            # Service 22 uses 2-byte PIDs
            pid = (data[0] << 8) | data[1]
            data = data[2:]  # Remove PID bytes

            param_key = (ServiceType.SERVICE_22.value, pid)
            commands = self.commands_by_parameter.get(param_key, [])

            command = next(
                (cmd for cmd in commands
                 if cmd.receive_address is None or
                 f"{cmd.receive_address:03X}" == can_id),
                None
            )

            if command:
                values = {}
                remaining_data = data
                for signal in command.signals:
                    try:
                        if isinstance(signal.format, Scaling):
                            value = signal.format.decode_value(remaining_data)
                        elif isinstance(signal.format, Enumeration):
                            value = signal.format.decode_value(remaining_data)
                        values[signal.id] = value
                    except Exception as e:
                        print(f"Error decoding signal {signal.id}: {e}")

                responses.append(CommandResponse(command, remaining_data, values))

            # Move to next parameter's data
            data = data[4:]  # Typical data length for service 22

        return responses

    def _extract_service_21_commands(self, can_id: str, data: bytes) -> List[CommandResponse]:
        responses = []
        while data:
            if len(data) < 1:
                break

            offset = data[0]
            data = data[1:]  # Remove offset byte

            param_key = (ServiceType.SERVICE_21.value, offset)
            commands = self.commands_by_parameter.get(param_key, [])

            command = next(
                (cmd for cmd in commands
                 if cmd.receive_address is None or
                 f"{cmd.receive_address:03X}" == can_id),
                None
            )

            if command:
                values = {}
                remaining_data = data
                for signal in command.signals:
                    if isinstance(signal.format, Scaling):
                        try:
                            if isinstance(signal.format, Scaling):
                                value = signal.format.decode_value(remaining_data)
                            elif isinstance(signal.format, Enumeration):
                                value = signal.format.decode_value(remaining_data)
                            values[signal.id] = value
                        except Exception as e:
                            print(f"Error decoding signal {signal.id}: {e}")

                responses.append(CommandResponse(command, remaining_data, values))

            # Move to next parameter's data
            data = data[2:]  # Typical data length for service 21

        return responses

def decode_obd_response(
        signalset: 'SignalSet',
        response_hex: str,
        can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled: Optional[bool] = None
        ) -> Dict[str, Any]:
    """Decode an OBD response using a signal set definition.

    Args:
        signalset: SignalSet instance containing signal definitions
        response_hex: Hex string of the OBD response

    Returns:
        Dictionary mapping signal IDs to their decoded values
    """
    # Create command registry
    registry = CommandRegistry(list(signalset.commands))

    # Parse CAN frames from response
    scanner = CANFrameScanner.from_ascii_string(
        response_hex,
        can_id_format=can_id_format,
        extended_addressing_enabled=extended_addressing_enabled
    )
    if not scanner:
        raise ValueError(f"Could not parse response: {response_hex}")

    # Process each CAN packet
    results = {}
    for packet in scanner:
        # Identify and decode commands
        command_responses = registry.identify_commands(packet)

        # Collect all decoded signal values
        for response in command_responses:
            results.update(response.values)

    return results
