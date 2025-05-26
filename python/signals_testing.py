import pytest
from typing import Any, Dict, Optional, Union
import glob
import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List, Callable, Set
import yaml.composer
import yaml.parser
import yaml.scanner
import yaml.tokens

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from can.can_frame import CANFrameScanner, CANIDFormat
from can.command_registry import decode_obd_response, get_model_year_command_registry
from can.signals import Command, SignalSet
from signalsets.loader import find_signalset_for_year, load_signalset


# Global cache for CommandRegistry instances by model year
_COMMAND_REGISTRY_CACHE = {}

class LineNumberPreservingLoader(yaml.SafeLoader):
    """
    A YAML Loader that preserves line numbers for mappings and sequences.
    This allows us to find the exact line number of a specific key-value in a YAML file.
    """
    def compose_node(self, parent, index):
        # The line number where the current node begins
        line = self.line
        node = super().compose_node(parent, index)
        node.__line__ = line + 1
        return node

    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        # Store the line number on the mapping
        mapping['__line__'] = node.__line__
        return mapping

    def construct_sequence(self, node, deep=False):
        sequence = super().construct_sequence(node, deep=deep)
        # Store the line number at which the sequence begins
        for idx, item in enumerate(sequence):
            if isinstance(item, dict) and '__line__' not in item:
                item['__line__'] = node.__line__
        return sequence


def find_signal_line_numbers(yaml_path: str) -> Dict[str, Dict[str, int]]:
    """
    Parse a YAML file and extract line numbers for all signal IDs within test cases.

    Args:
        yaml_path: Path to the YAML file

    Returns:
        Dictionary mapping test case index to a dictionary of signal IDs to line numbers
    """
    signal_line_numbers = {}

    try:
        with open(yaml_path, 'r') as f:
            yaml_content = f.read()

        # Parse the YAML with line number preservation
        data = yaml.load(yaml_content, Loader=LineNumberPreservingLoader)

        # Process test cases
        if 'test_cases' in data:
            for test_idx, test_case in enumerate(data['test_cases']):
                if 'expected_values' in test_case:
                    expected_values = test_case['expected_values']
                    test_line = test_case.get('__line__', 0)

                    # Create a dictionary for line numbers in this test case
                    signal_lines = {}

                    # Extract line numbers for each signal ID
                    for signal_id, _ in expected_values.items():
                        # Find the line by searching in the content
                        pattern = re.compile(r'(\s+)' + re.escape(signal_id) + r':', re.MULTILINE)

                        # Search in the content, but limit the search to lines after the test case start
                        lines = yaml_content.split('\n')
                        test_content = '\n'.join(lines[test_line-1:])
                        match = pattern.search(test_content)

                        if match:
                            # Calculate the real line number in the file
                            line_number = test_line + test_content[:match.end()].count('\n')
                            signal_lines[signal_id] = line_number

                    # Store the line numbers for this test case
                    signal_line_numbers[test_idx] = signal_lines

    except Exception as e:
        # If anything goes wrong, log it but don't break the tests
        print(f"Warning: Could not extract line numbers from {yaml_path}: {e}")

    return signal_line_numbers

def obd_testrunner_by_year(
        model_year: int,
        response_hex: str,
        expected_values: Dict[str, Any],
        can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled: Optional[bool] = None,
        signalsets_dir: Optional[str] = None,
        yaml_file: Optional[str] = None,
        test_case_idx: Optional[int] = None,
        signal_line_numbers: Optional[Dict[int, Dict[str, int]]] = None
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
        yaml_file: Path to the YAML file containing the test case
        test_case_idx: Index of the test case within the YAML file
        signal_line_numbers: Dictionary mapping test case indices to dictionaries of signal IDs to line numbers
    """
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
            # Get line number for more detailed error message
            line_info = ""
            if yaml_file and signal_line_numbers and test_case_idx is not None:
                if test_case_idx in signal_line_numbers and signal_id in signal_line_numbers[test_case_idx]:
                    line_number = signal_line_numbers[test_case_idx][signal_id]
                    line_info = f" (defined in {yaml_file}:{line_number})"

            assert signal_id in actual_values, f"Signal {signal_id} not found in decoded response{line_info}"
            actual_value = actual_values[signal_id]
            if isinstance(actual_value, (str)):
                assert actual_value == str(expected_value), \
                    f"Signal {signal_id} value mismatch{line_info}: got {actual_value}, expected {expected_value}"
            elif isinstance(expected_value, (int, float)):
                assert abs(actual_value - expected_value) < 1e-5, \
                    f"Signal {signal_id} value mismatch{line_info}: got {actual_value}, expected {expected_value}"
            else:
                assert actual_value == expected_value, \
                    f"Signal {signal_id} value mismatch{line_info}: got {actual_value}, expected {expected_value}"
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
                extended_addressing_enabled=extended_addressing_enabled,
                yaml_file=yaml_file,
                test_case_idx=test_case_idx,
                signal_line_numbers=signal_line_numbers
            )
        else:
            raise e

def obd_testrunner(
        signalset_json: str,
        response_hex: str,
        expected_values: Dict[str, Union[float, str]],
        can_id_format: CANIDFormat = CANIDFormat.ELEVEN_BIT,
        extended_addressing_enabled: Optional[bool] = None,
        yaml_file: Optional[str] = None,
        test_case_idx: Optional[int] = None,
        signal_line_numbers: Optional[Dict[int, Dict[str, int]]] = None
    ):
    """Test decoding an OBD response against expected values.

    Args:
        signalset_json: JSON string containing the signal set definition
        response_hex: Hex string of the OBD response
        expected_values: Dictionary mapping signal IDs to their expected values (numbers or strings)
        yaml_file: Path to the YAML file containing the test case
        test_case_idx: Index of the test case within the YAML file
        signal_line_numbers: Dictionary mapping test case indices to dictionaries of signal IDs to line numbers
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
        # Get line number for more detailed error message
        line_info = ""
        if yaml_file and signal_line_numbers and test_case_idx is not None:
            if test_case_idx in signal_line_numbers and signal_id in signal_line_numbers[test_case_idx]:
                line_number = signal_line_numbers[test_case_idx][signal_id]
                line_info = f" (defined in {yaml_file}:{line_number})"

        assert signal_id in actual_values, f"Signal {signal_id} not found in decoded response{line_info}"
        actual_value = actual_values[signal_id]
        if isinstance(expected_value, (int, float)):
            assert pytest.approx(actual_value) == expected_value, \
                f"Signal {signal_id} value mismatch{line_info}: got {actual_value}, expected {expected_value}"
        else:
            assert actual_value == expected_value, \
                f"Signal {signal_id} value mismatch{line_info}: got {actual_value}, expected {expected_value}"

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

    # Extract line numbers for each signal ID in each test case
    signal_line_numbers = find_signal_line_numbers(yaml_path)

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
        test_cases = test_data.get('test_cases', [])

        # Get the pre-computed registry for this model year so that we can determine the can format and extended addressing behavior
        registry = get_model_year_command_registry(model_year)

        command_id = test_data.get('command_id')
        command: Command = registry.commands_by_id.get(command_id)
        if command:
            default_can_format = command.protocol
            default_ext_addr = command.extended_address is not None
        else:
            default_can_format = CANIDFormat.ELEVEN_BIT
            default_ext_addr = None

        for test_idx, test_case in enumerate(test_cases):
            response_hex = test_case['response']
            expected_values = test_case['expected_values']

            obd_testrunner_by_year(
                model_year,
                response_hex,
                expected_values,
                can_id_format=default_can_format,
                extended_addressing_enabled=default_ext_addr,
                signalsets_dir=signalsets_dir,
                yaml_file=yaml_path,
                test_case_idx=test_idx,
                signal_line_numbers=signal_line_numbers
            )
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

        for test_idx, test_case in enumerate(test_cases):
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
                    signalsets_dir=signalsets_dir,
                    yaml_file=yaml_path,
                    test_case_idx=test_idx,
                    signal_line_numbers=signal_line_numbers
                )
            except Exception as e:
                raise type(e)(
                    f"Error in test case {test_idx} for model year {model_year}, "
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
