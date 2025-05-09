from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import os
import json
import time
import urllib.request
from pathlib import Path

from signalsets.loader import get_signalset_from_model_year

from .can_frame import CANPacket, CANFrameScanner, CANIDFormat
from .signals import Command, Enumeration, Scaling, SignalSet, Filter
from .repo_utils import extract_make_from_repo_name

# Cache directory for downloaded signal definitions
CACHE_DIR = Path(__file__).parent / ".cache"
SAEJ1979_URL = "https://raw.githubusercontent.com/OBDb/SAEJ1979/refs/heads/main/signalsets/v3/default.json"

# Global registry cache by model year
MODEL_YEAR_REGISTRY_CACHE: Dict[int, 'CommandRegistry'] = {}

def _strip_rax_values(json_data: str) -> str:
    """Remove 'rax' fields from the JSON data before parsing."""
    data = json.loads(json_data)
    for command in data.get('commands', []):
        command.pop('rax', None)
    return json.dumps(data)

def get_cached_saej1979_signals() -> List['Command']:
    """Fetch and cache the SAEJ1979 signal definitions."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = CACHE_DIR / "saej1979_signals.json"

    try:
        # If cache exists and is less than 24 hours old, use it
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 86400:
            with open(cache_file) as f:
                json_data = f.read()
                cleaned_data = _strip_rax_values(json_data)
                return SignalSet.from_json(cleaned_data).commands
    except Exception as e:
        print(f"Warning: Error reading cache: {e}")

    try:
        # Fetch fresh data
        with urllib.request.urlopen(SAEJ1979_URL) as response:
            json_data = response.read().decode('utf-8')
            cleaned_data = _strip_rax_values(json_data)
            # Cache the cleaned data
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_file, 'w') as f:
                f.write(cleaned_data)
            return SignalSet.from_json(cleaned_data).commands
    except Exception as e:
        print(f"Warning: Could not fetch SAEJ1979 signals: {e}")
        # If we have a cache file, use it even if it's old
        if cache_file.exists():
            with open(cache_file) as f:
                json_data = f.read()
                cleaned_data = _strip_rax_values(json_data)
                return SignalSet.from_json(cleaned_data).commands
        return []

class ServiceType(Enum):
    SERVICE_01 = 0x01
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

        if service == ServiceType.SERVICE_01.value:
            return self._extract_service_01_commands(packet.can_identifier, data)
        elif service == ServiceType.SERVICE_21.value:
            return self._extract_service_21_commands(packet.can_identifier, data)
        elif service == ServiceType.SERVICE_22.value:
            return self._extract_service_22_commands(packet.can_identifier, data)
        return []

    def _extract_service_22_commands(self, can_id: str, data: bytes) -> List[CommandResponse]:
        if not data or len(data) < 2:
            return []

        # Service 22 uses 2-byte PIDs
        pid = (data[0] << 8) | data[1]
        data = data[2:]  # Remove PID bytes

        param_key = (ServiceType.SERVICE_22.value, pid)
        # Prioritize the most recently-registered command by reversing the array.
        commands = reversed(self.commands_by_parameter.get(param_key, []))

        matched_commands = []
        matching_commands = []
        generic_commands = []

        for cmd in commands:
            if cmd.receive_address is not None and f"{cmd.receive_address:X}" == can_id:
                matching_commands.append(cmd)
            elif cmd.receive_address is None:
                generic_commands.append(cmd)

        # Use the first matching command if available, otherwise use generic command
        if matching_commands:
            matched_commands = [matching_commands[0]]
        elif generic_commands:
            matched_commands = generic_commands

        if not matched_commands:
            return []

        values = {}
        remaining_data = data
        responses = []
        for matched_command in matched_commands:
            for signal in matched_command.signals:
                try:
                    if isinstance(signal.format, Scaling):
                        value = signal.format.decode_value(remaining_data)
                    elif isinstance(signal.format, Enumeration):
                        value = signal.format.decode_value(remaining_data)
                    values[signal.id] = value
                except Exception as e:
                    print(f"Error decoding signal {signal.id}: {e}")
            responses.append(CommandResponse(matched_command, remaining_data, values))

        return responses

    def _extract_service_21_commands(self, can_id: str, data: bytes) -> List[CommandResponse]:
        if not data:
            return []

        offset = data[0]
        data = data[1:]  # Remove offset byte

        param_key = (ServiceType.SERVICE_21.value, offset)
        # Prioritize the most recently-registered command by reversing the array.
        commands = reversed(self.commands_by_parameter.get(param_key, []))

        matched_commands = []
        matching_commands = []
        generic_commands = []

        for cmd in commands:
            if cmd.receive_address is not None and f"{cmd.receive_address:X}" == can_id:
                matching_commands.append(cmd)
            elif cmd.receive_address is None:
                generic_commands.append(cmd)

        # Use the first matching command if available, otherwise use generic command
        if matching_commands:
            matched_commands = [matching_commands[0]]
        elif generic_commands:
            matched_commands = generic_commands

        if not matched_commands:
            return []

        values = {}
        remaining_data = data
        responses = []
        for matched_command in matched_commands:
            for signal in matched_command.signals:
                try:
                    if isinstance(signal.format, Scaling):
                        value = signal.format.decode_value(remaining_data)
                    elif isinstance(signal.format, Enumeration):
                        value = signal.format.decode_value(remaining_data)
                    values[signal.id] = value
                except Exception as e:
                    print(f"Error decoding signal {signal.id}: {e}")
            responses.append(CommandResponse(matched_command, remaining_data, values))

        return responses

    def _extract_service_01_commands(self, can_id: str, data: bytes) -> List[CommandResponse]:
        if not data:
            return []

        pid = data[0]
        data = data[1:]  # Remove PID byte

        param_key = (ServiceType.SERVICE_01.value, pid)
        # Prioritize the most recently-registered command by reversing the array.
        commands = reversed(self.commands_by_parameter.get(param_key, []))

        # Sort commands to prioritize those with a specific receive address matching the CAN ID
        # before falling back to commands without a receive address filter
        matching_commands = []
        generic_commands = []

        for cmd in commands:
            if cmd.receive_address is not None and f"{cmd.receive_address:X}" == can_id:
                matching_commands.append(cmd)
            elif cmd.receive_address is None:
                generic_commands.append(cmd)

        # Use the first matching command if available, otherwise use generic command
        matched_command = None
        if matching_commands:
            matched_command = matching_commands[0]
        elif generic_commands:
            matched_command = generic_commands[0]

        if not matched_command:
            return []

        values = {}
        remaining_data = data
        for signal in matched_command.signals:
            try:
                if isinstance(signal.format, Scaling):
                    value = signal.format.decode_value(remaining_data)
                elif isinstance(signal.format, Enumeration):
                    value = signal.format.decode_value(remaining_data)
                values[signal.id] = value
            except Exception as e:
                print(f"Error decoding signal {signal.id}: {e}")

        return [CommandResponse(matched_command, remaining_data, values)]


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
    # Get SAEJ1979 base signals and combine with provided signals
    saej1979_commands = get_cached_saej1979_signals()
    combined_commands = list(saej1979_commands) + list(signalset.commands)

    # Create command registry with combined commands
    registry = CommandRegistry(combined_commands)

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

def get_model_year_command_registry(model_year: int) -> 'CommandRegistry':
    """Get or create a cached CommandRegistry for a specific model year.

    This function is optimized to compute the registry only once per model year and
    reuse it for all subsequent calls, significantly improving performance for
    test suites running many tests for the same model year.

    Args:
        model_year: The vehicle model year to get a registry for

    Returns:
        CommandRegistry instance for the specified model year
    """
    # Check if we already have a cached registry for this model year
    if model_year in MODEL_YEAR_REGISTRY_CACHE:
        return MODEL_YEAR_REGISTRY_CACHE[model_year]

    try:
        # Get the appropriate signalset for this model year
        signalset_json = get_signalset_from_model_year(model_year)
        signalset = SignalSet.from_json(signalset_json)

        # Get SAE J1979 base signals
        saej1979_commands = get_cached_saej1979_signals()

        # Check if the model-specific signalset is empty and we need to use the make repo
        if not signalset.commands:
            # Extract the make from the repo name using our utility function
            make = extract_make_from_repo_name()

            if make:
                # Try to fetch the make's signalset
                make_url = f"https://raw.githubusercontent.com/OBDb/{make}/refs/heads/main/signalsets/v3/default.json"

                try:
                    import urllib.request
                    import time
                    import json

                    # Create cache dir if not exists
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    cache_file = CACHE_DIR / f"{make.lower()}_signals.json"

                    try:
                        # If cache exists and is less than 24 hours old, use it
                        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 86400:
                            with open(cache_file) as f:
                                json_data = f.read()
                                make_signalset = SignalSet.from_json(json_data)
                                print(f"Using cached {make} signals for model year {model_year}")
                                signalset = make_signalset
                    except Exception as e:
                        print(f"Warning: Error reading {make} cache: {e}")

                    # If we don't have valid cached data, fetch it
                    if not signalset.commands:
                        with urllib.request.urlopen(make_url) as response:
                            json_data = response.read().decode('utf-8')

                            with open(cache_file, 'w') as f:
                                f.write(json_data)

                            make_signalset = SignalSet.from_json(json_data)
                            signalset = make_signalset
                            print(f"Fetched and using {make} signals for model year {model_year}")

                except Exception as e:
                    print(f"Warning: Could not fetch {make} signals: {e}")

        # Combine signals from SAE J1979 and model-specific or make-specific signals
        combined_commands = list(saej1979_commands) + list(signalset.commands)

        # Filter combined_commands by each command's optional .filter property.
        if model_year is not None:
            filtered_commands = []
            for cmd in combined_commands:
                if cmd.filter is None or cmd.filter.matches(model_year):
                    filtered_commands.append(cmd)
            combined_commands = filtered_commands

        # Create and cache the registry
        registry = CommandRegistry(combined_commands)
        MODEL_YEAR_REGISTRY_CACHE[model_year] = registry

        return registry
    except Exception as e:
        raise ValueError(f"Failed to create CommandRegistry for model year {model_year}: {str(e)}")
