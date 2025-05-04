"""
Module for updating YAML test cases with current signal values.
This is useful when signals are removed from signalsets and tests need to be updated.
"""

import os
import glob
import yaml
from typing import Dict, List, Any, Tuple, Optional

from .signals_testing import CANIDFormat, CANFrameScanner
from can.command_registry import get_model_year_command_registry

# Custom YAML formatting for multi-line strings
class LiteralString(str):
    pass

def literal_string_representer(dumper, data):
    """Custom representer for multi-line strings that preserves formatting."""
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

# Add custom representer to PyYAML
yaml.add_representer(LiteralString, literal_string_representer)

def load_yaml_file(yaml_path: str) -> Dict:
    """Load and parse a YAML file."""
    try:
        with open(yaml_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Error loading YAML file {yaml_path}: {str(e)}")

def save_yaml_file(yaml_path: str, data: Dict) -> None:
    """Save data to a YAML file, preserving formatting where possible."""
    try:
        # Process multi-line string values to use literal block format
        _format_multi_line_strings(data)

        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise RuntimeError(f"Error saving YAML file {yaml_path}: {str(e)}")

def _format_multi_line_strings(data: Any) -> None:
    """
    Recursively process a data structure and wrap multi-line strings
    with our custom LiteralString class to preserve formatting.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and '\n' in value:
                # Use our custom string type for multi-line strings
                data[key] = LiteralString(value)
            elif isinstance(value, (dict, list)):
                _format_multi_line_strings(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str) and '\n' in item:
                data[i] = LiteralString(item)
            elif isinstance(item, (dict, list)):
                _format_multi_line_strings(item)

def get_model_year_from_path(yaml_path: str) -> Optional[int]:
    """Extract model year from a YAML file path."""
    parts = yaml_path.split(os.sep)
    for part in parts:
        if part.isdigit() and 1990 <= int(part) <= 2050:  # Reasonable year range
            return int(part)
    return None

def collect_test_cases_for_update(test_cases_dir: str, specific_model_years: List[int] = None) -> List[Tuple[str, int]]:
    """
    Find all command test YAML files that need updating.

    Args:
        test_cases_dir: Directory containing test cases
        specific_model_years: Optional list of model years to filter by

    Returns:
        List of (yaml_path, model_year) tuples
    """
    all_yaml_files = []

    # Find all model year directories
    year_dirs = [d for d in os.listdir(test_cases_dir) if os.path.isdir(os.path.join(test_cases_dir, d)) and d.isdigit()]

    # Filter to specific years if requested
    if specific_model_years:
        year_dirs = [year for year in year_dirs if int(year) in specific_model_years]

    for year_dir in year_dirs:
        model_year = int(year_dir)

        # Find command files
        commands_dir = os.path.join(test_cases_dir, year_dir, "commands")
        if os.path.exists(commands_dir):
            for yaml_file in glob.glob(os.path.join(commands_dir, "*.yaml")):
                all_yaml_files.append((yaml_file, model_year))

    return all_yaml_files

def format_value(value):
    """
    Format numeric values to have consistent decimal places.

    Args:
        value: The value to format

    Returns:
        Formatted value with at most 5 decimal places for floats
    """
    if isinstance(value, float):
        # Format with up to 5 decimal places, removing trailing zeros
        formatted = f"{value:.5f}".rstrip('0').rstrip('.')
        return float(formatted)  # Convert back to float to ensure proper YAML serialization
    return value

def process_yaml_file(yaml_path: str, model_year: int, dry_run: bool = False, verbose: bool = False):
    """
    Process a single YAML test file and update expected values based on current signalset.

    Args:
        yaml_path: Path to the YAML test file
        model_year: Model year for finding the correct signalset
        dry_run: If True, don't actually update files
        verbose: If True, show detailed output
    """
    if verbose:
        print(f"Processing {yaml_path} for model year {model_year}...")

    # Load the test file
    yaml_data = load_yaml_file(yaml_path)
    if not yaml_data or 'test_cases' not in yaml_data:
        if verbose:
            print(f"Skipping {yaml_path} - no test cases found")
        return

    # Extract test configuration
    can_id_format_str = yaml_data.get('can_id_format', 'ELEVEN_BIT')
    can_id_format = getattr(CANIDFormat, can_id_format_str)
    ext_addressing = yaml_data.get('extended_addressing_enabled', False)

    # Track changes to report
    changes_made = False
    signals_removed = set()
    signals_updated = {}

    # Process each test case
    for test_idx, test_case in enumerate(yaml_data['test_cases']):
        if 'response' not in test_case or 'expected_values' not in test_case:
            continue

        response_hex = test_case['response']
        original_expected = test_case['expected_values'].copy()

        # Make sure response is a LiteralString if it contains newlines
        if isinstance(response_hex, str) and '\n' in response_hex:
            test_case['response'] = LiteralString(response_hex)

        # Get all actual values using current signalset
        try:
            scanner = CANFrameScanner.from_ascii_string(
                response_hex,
                can_id_format=can_id_format,
                extended_addressing_enabled=ext_addressing
            )
            if not scanner:
                if verbose:
                    print(f"  Warning: Could not parse response in test case {test_idx+1}")
                continue

            # Process the response with current signalset
            current_values = {}
            try:
                # Use current signalset to decode
                registry = get_model_year_command_registry(model_year)

                for packet in scanner:
                    command_responses = registry.identify_commands(packet)
                    for response in command_responses:
                        # Format float values to have consistent decimal places
                        formatted_values = {k: format_value(v) for k, v in response.values.items()}
                        current_values.update(formatted_values)

            except Exception as e:
                if verbose:
                    print(f"  Error decoding response: {str(e)}")
                continue

            # Update expected values
            new_expected = {}
            for signal_id, expected_value in original_expected.items():
                if signal_id in current_values:
                    # Signal still exists, keep it (possibly with updated value)
                    if verbose and current_values[signal_id] != expected_value:
                        signals_updated[signal_id] = (expected_value, current_values[signal_id])
                    new_expected[signal_id] = current_values[signal_id]
                else:
                    # Signal no longer exists
                    signals_removed.add(signal_id)

            # Check if we need to update the test case
            if new_expected != original_expected:
                changes_made = True
                if not dry_run:
                    test_case['expected_values'] = new_expected

        except Exception as e:
            if verbose:
                print(f"  Error processing test case {test_idx+1}: {str(e)}")
            continue

    # Save the updated file if changes were made
    if changes_made:
        if verbose:
            if signals_removed:
                print(f"  Signals removed: {', '.join(signals_removed)}")
            if signals_updated:
                for signal_id, (old_val, new_val) in signals_updated.items():
                    print(f"  Signal {signal_id} updated: {old_val} -> {new_val}")

        if not dry_run:
            save_yaml_file(yaml_path, yaml_data)
            print(f"Updated {yaml_path}")
        else:
            print(f"Would update {yaml_path} (dry run)")
    elif verbose:
        print(f"  No changes needed for {yaml_path}")

def update_yaml_tests(test_cases_dir: str, specific_years: List[int] = None, dry_run: bool = False, verbose: bool = False):
    """
    Find and update all YAML test files matching the criteria.

    Args:
        test_cases_dir: Path to the test_cases directory
        specific_years: Optional list of specific model years to update
        dry_run: If True, don't actually update files
        verbose: If True, show detailed output

    Returns:
        Number of files processed
    """
    # Find all YAML test files by model year
    test_files = collect_test_cases_for_update(test_cases_dir, specific_years)
    if not test_files:
        print("No test files found matching criteria.")
        return 0

    print(f"Found {len(test_files)} test files to process.")

    # Process each file
    for yaml_path, model_year in test_files:
        process_yaml_file(yaml_path, model_year, dry_run, verbose)

    return len(test_files)