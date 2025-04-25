import pytest
from typing import Any, Dict, Optional, Union
import glob
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Set, Tuple, Union, List

from .can_frame import CANIDFormat
from .command_registry import decode_obd_response
from .signals import SignalSet

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

    Args:
        model_year: Model year to use for finding the appropriate signalset
        response_hex: Hex string of the OBD response
        expected_values: Dictionary mapping signal IDs to their expected values
        can_id_format: CAN ID format to use for parsing
        extended_addressing_enabled: Whether extended addressing is enabled
        signalsets_dir: Optional explicit path to signalsets directory
    """
    try:
        signalset_json = get_signalset_from_model_year(model_year)
    except FileNotFoundError as e:
        if signalsets_dir:
            # Try the explicitly provided directory
            signalset_path = find_signalset_for_year(model_year, signalsets_dir)
            signalset_json = load_signalset(signalset_path)
        else:
            raise e

    obd_testrunner(
        signalset_json,
        response_hex,
        expected_values,
        can_id_format=can_id_format,
        extended_addressing_enabled=extended_addressing_enabled
    )

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

    model_year = test_data['model_year']
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
