import pytest
from typing import Any, Dict, Optional, Union
import glob
import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Set, Tuple, Union, List, Callable

from .can_frame import CANFrameScanner, CANIDFormat
from .command_registry import decode_obd_response, CommandRegistry, get_cached_saej1979_signals
from .signals import SignalSet

# Global cache for CommandRegistry instances by model year
_COMMAND_REGISTRY_CACHE = {}

class YearRange:
    """A class to represent and compare year ranges from filenames."""

    def __init__(self, filename: str):
        self.filename = filename
        self.start_year = None
        self.end_year = None
        self.single_year = None
        self._parse_filename(filename)

    def _parse_filename(self, filename: str):
        """Parse a filename to extract year range information."""
        # Remove file extension
        basename = os.path.basename(filename)
        name_part = os.path.splitext(basename)[0]

        # Try to match different filename patterns

        # Pattern 1: YYYY-YYYY.json (year range)
        range_match = re.match(r'^(\d{4})-(\d{4})$', name_part)
        if range_match:
            self.start_year = int(range_match.group(1))
            self.end_year = int(range_match.group(2))
            return

        # Pattern 2: YYYY.json (single year)
        single_match = re.match(r'^(\d{4})$', name_part)
        if single_match:
            self.single_year = int(single_match.group(1))
            self.start_year = self.single_year
            self.end_year = self.single_year
            return

        # Pattern 3: model-YYYY.json or model-YYYY-YYYY.json
        model_range_match = re.search(r'-(\d{4})-(\d{4})$', name_part)
        if model_range_match:
            self.start_year = int(model_range_match.group(1))
            self.end_year = int(model_range_match.group(2))
            return

        model_year_match = re.search(r'-(\d{4})$', name_part)
        if model_year_match:
            self.single_year = int(model_year_match.group(1))
            self.start_year = self.single_year
            self.end_year = self.single_year
            return

        # Default: Consider as default.json or fallback case
        self.start_year = 0
        self.end_year = 9999  # Far future

    def contains_year(self, year: int) -> bool:
        """Check if this range contains the specified year."""
        if self.start_year is None or self.end_year is None:
            return False
        return self.start_year <= year <= self.end_year

    def __str__(self) -> str:
        if self.single_year is not None:
            return f"{self.single_year} ({self.filename})"
        if self.start_year == 0 and self.end_year == 9999:
            return f"default ({self.filename})"
        return f"{self.start_year}-{self.end_year} ({self.filename})"

def find_signalsets_directory() -> str:
    """
    Find the signalsets directory by searching relative to the current file
    and common repository structures.

    Returns:
        Path to the signalsets directory

    Raises:
        FileNotFoundError: If signalsets directory cannot be found
    """
    # List of potential relative paths to try
    potential_paths = [
        # Path in the same repo
        Path(__file__).parent.parent / 'signalsets' / 'v3',

        # Path if schemas is a submodule in tests/schemas
        Path(__file__).parent.parent.parent.parent / 'signalsets' / 'v3',

        # Path if schemas is cloned into tests/schemas
        Path(__file__).parent.parent.parent / 'signalsets' / 'v3',

        # Path relative to working directory
        Path('signalsets') / 'v3',
        Path('tests') / 'signalsets' / 'v3',
    ]

    # Try each path
    for path in potential_paths:
        if path.exists() and path.is_dir():
            return str(path)

    # If a SIGNALSETS_DIR environment variable is set, try that
    env_path = os.environ.get('SIGNALSETS_DIR')
    if env_path and os.path.exists(env_path) and os.path.isdir(env_path):
        return env_path

    # If we got here, we couldn't find the directory
    raise FileNotFoundError(
        "Could not find signalsets directory. Please set the SIGNALSETS_DIR "
        "environment variable to the path of your signalsets/v3 directory."
    )

def find_signalset_for_year(model_year: int, signalsets_dir: Optional[str] = None) -> str:
    """
    Find the appropriate signalset file for a given model year.

    Args:
        model_year: The model year to find a signalset for
        signalsets_dir: Optional path to signalsets directory

    Returns:
        Path to the matching signalset file

    Raises:
        FileNotFoundError: If no suitable signalset is found
    """
    # Get signalsets directory if not provided
    if signalsets_dir is None:
        try:
            signalsets_dir = find_signalsets_directory()
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Could not locate signalsets directory: {e}")

    # Get all JSON files in the directory
    json_files = glob.glob(os.path.join(signalsets_dir, '*.json'))

    if not json_files:
        raise FileNotFoundError(
            f"No JSON files found in signalsets directory: {signalsets_dir}"
        )

    # Process each file to determine its year range
    year_ranges = [YearRange(file) for file in json_files]

    # Filter to those that contain the specified model year
    matching_ranges = [yr for yr in year_ranges if yr.contains_year(model_year)]

    # If we have matches, take the most specific one
    if matching_ranges:
        # Sort by range size (ascending) so most specific comes first
        matching_ranges.sort(key=lambda yr: yr.end_year - yr.start_year)
        return matching_ranges[0].filename

    # Look for a default.json file
    default_file = os.path.join(signalsets_dir, 'default.json')
    if os.path.exists(default_file):
        return default_file

    # If we get here, we couldn't find a suitable file
    raise FileNotFoundError(
        f"No signalset found for model year {model_year} in {signalsets_dir}"
    )

def load_signalset(filename: str) -> str:
    """
    Load a signalset JSON file from either an absolute path or relative to signalsets directory.

    Args:
        filename: Path to the signalset file (absolute or relative to signalsets dir)

    Returns:
        Contents of the signalset file as a string
    """
    if os.path.isabs(filename):
        signalset_path = filename
    else:
        try:
            signalsets_dir = find_signalsets_directory()
            signalset_path = os.path.join(signalsets_dir, os.path.basename(filename))
        except FileNotFoundError:
            # If we can't find the signalsets directory, try using the filename as-is
            signalset_path = filename

    try:
        with open(signalset_path) as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Signalset file not found: {signalset_path}")

def get_signalset_from_model_year(model_year: int) -> str:
    """
    Get the signalset JSON content for a specific model year.

    Args:
        model_year: The model year to find a signalset for

    Returns:
        Signalset JSON content as a string
    """
    signalset_path = find_signalset_for_year(model_year)
    return load_signalset(signalset_path)

def obd_testrunner_by_year(
        model_year: int,
        response_hex: str,
        expected_values: Dict[str, Any],
        can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled: Optional[bool] = None,
        signalsets_dir: Optional[str] = None
    ):
    """
    Test signal decoding against known responses using a signalset inferred from model year.
    Uses cached CommandRegistry instances for better performance.

    Args:
        model_year: Model year to use for finding the appropriate signalset
        response_hex: Hex string of the OBD response
        expected_values: Dictionary mapping signal IDs to their expected values
        can_id_format: CAN ID format to use for parsing
        extended_addressing_enabled: Whether extended addressing is enabled
        signalsets_dir: Optional explicit path to signalsets directory
    """
    from .command_registry import get_model_year_command_registry

    try:
        # Get the pre-computed registry for this model year
        registry = get_model_year_command_registry(model_year)

        # Parse CAN frames from response
        scanner = CANFrameScanner.from_ascii_string(
            response_hex,
            can_id_format=can_id_format,
            extended_addressing_enabled=extended_addressing_enabled
        )
        if not scanner:
            raise ValueError(f"Could not parse response: {response_hex}")

        # Process each CAN packet using the cached registry
        actual_values = {}
        for packet in scanner:
            # Identify and decode commands
            command_responses = registry.identify_commands(packet)

            # Collect all decoded signal values
            for response in command_responses:
                actual_values.update(response.values)

        # Test each expected signal value
        for signal_id, expected_value in expected_values.items():
            assert signal_id in actual_values, f"Signal {signal_id} not found in decoded response"
            actual_value = actual_values[signal_id]
            if isinstance(expected_value, (int, float)):
                assert pytest.approx(actual_value) == expected_value, \
                    f"Signal {signal_id} value mismatch: got {actual_value}, expected {expected_value}"
            else:
                assert actual_value == expected_value, \
                    f"Signal {signal_id} value mismatch: got {actual_value}, expected {expected_value}"
    except FileNotFoundError as e:
        if signalsets_dir:
            # Use the original implementation as fallback with explicit signalsets directory
            signalset_path = find_signalset_for_year(model_year, signalsets_dir)
            signalset_json = load_signalset(signalset_path)
            obd_testrunner(
                signalset_json,
                response_hex,
                expected_values,
                can_id_format=can_id_format,
                extended_addressing_enabled=extended_addressing_enabled
            )
        else:
            raise e

def list_available_signalsets(signalsets_dir: Optional[str] = None) -> List[str]:
    """
    List all available signalset files with their year ranges.

    Args:
        signalsets_dir: Optional path to signalsets directory

    Returns:
        List of signalset files with year range info
    """
    if signalsets_dir is None:
        try:
            signalsets_dir = find_signalsets_directory()
        except FileNotFoundError:
            return ["No signalsets directory found"]

    json_files = glob.glob(os.path.join(signalsets_dir, '*.json'))
    if not json_files:
        return [f"No JSON files found in {signalsets_dir}"]

    year_ranges = [YearRange(file) for file in json_files]

    return [str(yr) for yr in year_ranges]

def obd_testrunner(
        signalset_json: str,
        response_hex: str,
        expected_values: Dict[str, Union[float, str]],  # Updated type hint
        can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled: Optional[bool] = None
    ):
    """Test decoding an OBD response against expected values.

    Args:
        signalset_json: JSON string containing the signal set definition
        response_hex: Hex string of the OBD response
        expected_values: Dictionary mapping signal IDs to their expected values (numbers or strings)
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
        if isinstance(expected_value, (int, float)):
            assert pytest.approx(actual_value) == expected_value, \
                f"Signal {signal_id} value mismatch: got {actual_value}, expected {expected_value}"
        else:
            assert actual_value == expected_value, \
                f"Signal {signal_id} value mismatch: got {actual_value}, expected {expected_value}"

def find_yaml_test_cases(test_cases_dir: str) -> Dict[int, str]:
    """
    Find all YAML test case files and group them by model year.

    Args:
        test_cases_dir: Directory containing YAML test case files

    Returns:
        Dictionary mapping model years to YAML file paths
    """
    yaml_files = {}
    for ext in ('yaml', 'yml'):
        for file_path in glob.glob(os.path.join(test_cases_dir, f'*.{ext}')):
            try:
                with open(file_path, 'r') as f:
                    test_data = yaml.safe_load(f)
                    if 'model_year' in test_data:
                        yaml_files[test_data['model_year']] = file_path
            except (yaml.YAMLError, KeyError):
                continue
    return yaml_files

def obd_yaml_testrunner(
        yaml_path: str,
        signalsets_dir: Optional[str] = None
    ):
    """
    Run OBD tests from a YAML test case file.

    Args:
        yaml_path: Path to the YAML test case file
        signalsets_dir: Optional explicit path to signalsets directory

    Raises:
        FileNotFoundError: If the YAML file or signalset cannot be found
        yaml.YAMLError: If the YAML file is invalid
    """
    with open(yaml_path, 'r') as f:
        test_data = yaml.safe_load(f)

    # Check for new vs old format
    if 'command_id' in test_data:
        # This is a command-specific test file (new format)
        model_year = None

        # Try to extract model year from directory structure
        # Typical path: .../test_cases/2022/commands/0101.yaml
        try:
            dir_path = os.path.dirname(yaml_path)
            cmd_dir = os.path.basename(dir_path)
            if cmd_dir == 'commands':
                year_dir = os.path.basename(os.path.dirname(dir_path))
                if year_dir.isdigit():
                    model_year = int(year_dir)
        except Exception:
            pass

        # If we couldn't extract from path, look for support file
        if model_year is None:
            support_path = os.path.join(os.path.dirname(os.path.dirname(yaml_path)), 'command_support.yaml')
            try:
                if os.path.exists(support_path):
                    with open(support_path, 'r') as f:
                        support_data = yaml.safe_load(f)
                        model_year = support_data.get('model_year')
            except Exception:
                pass

        # If we still don't have a model year, raise an error
        if model_year is None:
            raise ValueError(f"Could not determine model year for command file: {yaml_path}")

        # Get command-specific test defaults
        default_can_format = getattr(CANIDFormat, test_data.get('can_id_format', 'ELEVEN_BIT'))
        default_ext_addr = test_data.get('extended_addressing_enabled', None)
        test_cases = test_data.get('test_cases', [])

        for test_case in test_cases:
            response_hex = test_case['response']
            expected_values = test_case['expected_values']

            try:
                obd_testrunner_by_year(
                    model_year,
                    response_hex,
                    expected_values,
                    can_id_format=default_can_format,
                    extended_addressing_enabled=default_ext_addr,
                    signalsets_dir=signalsets_dir
                )
            except Exception as e:
                raise type(e)(
                    f"Error in command {test_data.get('command_id')} test case for model year {model_year}, "
                    f"response {response_hex}: {str(e)}"
                ) from e
    elif 'model_year' in test_data and 'test_cases' in test_data:
        # This is either a full test case file (old format) or command_support.yaml (new format)
        model_year = test_data['model_year']

        # Check if this is a command_support file with no test cases
        if len(test_data.get('test_cases', [])) == 0:
            # This is a command_support file with no test cases
            return

        # Process as standard test case file
        test_cases = test_data['test_cases']

        # Get file-level defaults
        default_can_format = getattr(CANIDFormat, test_data.get('can_id_format', 'ELEVEN_BIT'))
        default_ext_addr = test_data.get('extended_addressing_enabled', None)

        for test_case in test_cases:
            response_hex = test_case['response']
            expected_values = test_case['expected_values']

            # Get per-test case settings or use defaults
            test_can_format = getattr(CANIDFormat, test_case.get('can_id_format', '')) if 'can_id_format' in test_case else default_can_format
            test_ext_addr = test_case.get('extended_addressing_enabled', default_ext_addr)

            try:
                obd_testrunner_by_year(
                    model_year,
                    response_hex,
                    expected_values,
                    can_id_format=test_can_format,
                    extended_addressing_enabled=test_ext_addr,
                    signalsets_dir=signalsets_dir
                )
            except Exception as e:
                raise type(e)(
                    f"Error in test case for model year {model_year}, "
                    f"response {response_hex}: {str(e)}"
                ) from e
    else:
        raise ValueError(f"Invalid test file format in {yaml_path}. Neither 'command_id' nor 'model_year'+'test_cases' found.")

def find_test_yaml_files(test_cases_dir: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Find all test YAML files in the directory structure, grouped by model year.

    Args:
        test_cases_dir: Path to the directory containing test cases

    Returns:
        Dictionary with model year as key and a list of (test_id, yaml_path) tuples as value
    """
    test_files_by_year = {}

    try:
        model_year_dirs = [d for d in os.listdir(test_cases_dir)
                         if os.path.isdir(os.path.join(test_cases_dir, d)) and d.isdigit()]
    except (FileNotFoundError, NotADirectoryError):
        return {}

    for year_dir in model_year_dirs:
        year_key = f"MY{year_dir}"
        test_files_by_year[year_key] = []

        # Get command files only (skip command_support.yaml)
        commands_dir = os.path.join(test_cases_dir, year_dir, "commands")
        if os.path.exists(commands_dir):
            for cmd_file in glob.glob(os.path.join(commands_dir, "*.yaml")):
                cmd_id = os.path.splitext(os.path.basename(cmd_file))[0]
                test_id = f"cmd_{cmd_id}"
                test_files_by_year[year_key].append((test_id, cmd_file))

    return test_files_by_year

def register_test_classes(test_files_by_year: Dict[str, List[Tuple[str, str]]],
                         runner_func: Callable[[str], None] = None,
                         target_module=None):
    """
    Dynamically create and register test classes grouped by model year.
    Precomputes CommandRegistry instances for each model year to optimize test execution.

    Args:
        test_files_by_year: Dictionary mapping model year keys to lists of (test_id, yaml_path) tuples
        runner_func: Function to use for running tests (defaults to obd_yaml_testrunner)
        target_module: Module where test classes should be registered (defaults to caller's module)
    """
    if runner_func is None:
        runner_func = obd_yaml_testrunner

    if target_module is None:
        # Get the caller's module (usually __main__ or the importing module)
        target_module = sys.modules[sys._getframe(1).f_globals['__name__']]

    # Import the command registry function here to avoid circular imports
    from .command_registry import get_model_year_command_registry

    # Precompute CommandRegistry instances for each model year
    # This significantly improves performance for parallel test execution
    for year_key in test_files_by_year.keys():
        if not year_key.startswith("MY") or not year_key[2:].isdigit():
            continue

        model_year = int(year_key[2:])
        try:
            # This will compute and cache the registry for this model year
            get_model_year_command_registry(model_year)
            print(f"Precomputed CommandRegistry for {year_key}")
        except Exception as e:
            print(f"Warning: Failed to precompute CommandRegistry for {year_key}: {str(e)}")

    # Create test classes dynamically for each model year
    for year_key, test_files in test_files_by_year.items():
        # Skip years with no test files
        if not test_files:
            continue

        # Define a test class for this model year
        class_name = f"Test{year_key}"
        test_class = type(class_name, (), {})

        # Add the test method for each command file in this year
        for idx, (test_id, yaml_path) in enumerate(test_files):
            # Create a test method with proper name
            test_method_name = f"test_{test_id}"

            # Define a closure to capture the current yaml_path
            def make_test_method(path, run_func):
                def test_method(self):
                    try:
                        run_func(path)
                    except Exception as e:
                        pytest.fail(f"Failed to run tests from {path}: {e}")
                return test_method

            # Add the test method to the class
            setattr(test_class, test_method_name, make_test_method(yaml_path, runner_func))

        # Add the class to the target module
        setattr(target_module, class_name, test_class)

    return True
