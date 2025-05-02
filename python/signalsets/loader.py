import glob
import os
from pathlib import Path
from typing import List, Optional

from .year_range import YearRange

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
        Path(__file__).parent.parent.parent / 'signalsets' / 'v3',

        # Path if schemas is a submodule in tests/schemas
        Path(__file__).parent.parent.parent.parent.parent / 'signalsets' / 'v3',

        # Path if schemas is cloned into tests/schemas
        Path(__file__).parent.parent.parent.parent / 'signalsets' / 'v3',

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
