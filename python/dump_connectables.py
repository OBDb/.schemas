#!/usr/bin/env python3
"""
Dump connectables from signalset files to a JSON file.

This script scans a directory for all JSON files, extracts signals that have
a 'suggestedMetric' property from each file, and creates a mapping where:
- Keys are the relative paths to the JSON files
- Values are dictionaries mapping signal IDs to their suggestedMetric values
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the path so we can import the signalsets module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from python.signalsets.loader import load_signalset
except ImportError:
    print("Error: Could not import signalsets module. Make sure you're running this from the root directory.")
    sys.exit(1)


def extract_connectables(signalset_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract all signals with a 'suggestedMetric' property from a signalset.

    Args:
        signalset_data: The parsed JSON data of the signalset

    Returns:
        A dictionary mapping signal IDs to their suggestedMetric values
    """
    connectables = {}

    # Process individual signals in each command
    if "commands" in signalset_data:
        for command in signalset_data["commands"]:
            if "signals" in command:
                for signal in command["signals"]:
                    if "suggestedMetric" in signal:
                        connectables[signal["id"]] = signal["suggestedMetric"]

    # Process signal groups if they exist
    if "signalGroups" in signalset_data:
        for group in signalset_data["signalGroups"]:
            if "suggestedMetricGroup" in group:
                connectables[group["id"]] = group["suggestedMetricGroup"]

    return connectables


def process_directory(directory_path: str) -> Dict[str, Dict[str, str]]:
    """
    Process all JSON files in a directory, extracting connectables from each.

    Args:
        directory_path: Path to the directory to scan for JSON files

    Returns:
        Dictionary mapping relative file paths to their connectables
    """
    results = {}
    base_dir = Path(directory_path)

    # Regex pattern to match YYYY-YYYY.json (where YYYY is a 4-digit year)
    year_range_pattern = re.compile(r'^\d{4}-\d{4}\.json$', re.IGNORECASE)

    # Walk the directory tree to find all JSON files
    for root, _, files in os.walk(directory_path):
        for file in files:
            # Only include json files that match either default.json or YYYY-YYYY.json
            if file.lower() == 'default.json' or year_range_pattern.match(file):
                file_path = os.path.join(root, file)

                # Get the relative path to use as the key
                rel_path = os.path.relpath(file_path, directory_path)

                try:
                    # Load and process the signalset
                    try:
                        signalset_content = load_signalset(file_path)
                        signalset_data = json.loads(signalset_content)
                    except Exception:
                        # If the signalset loader fails, try loading as a regular JSON file
                        with open(file_path, 'r') as f:
                            signalset_data = json.load(f)

                    # Extract connectables
                    connectables = extract_connectables(signalset_data)

                    # Only include files that have connectables
                    if connectables:
                        results[rel_path] = connectables
                        print(f"Processed {rel_path}: found {len(connectables)} connectables")
                    else:
                        print(f"No connectables found in {rel_path}")

                except Exception as e:
                    print(f"Error processing {rel_path}: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Extract connectables from all JSON files in a directory.'
    )
    parser.add_argument(
        'path',
        help='Path to a directory to scan for JSON files'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path. If not specified, a default name will be used based on the input directory'
    )

    args = parser.parse_args()

    # Check if the input path exists and is a directory
    input_path = args.path
    if not os.path.exists(input_path):
        print(f"Error: Path does not exist: {input_path}")
        sys.exit(1)

    if not os.path.isdir(input_path):
        print(f"Error: Path is not a directory: {input_path}")
        sys.exit(1)

    # Set the output path
    if args.output:
        output_path = args.output
    else:
        # Use the directory name for the output file
        dir_name = os.path.basename(os.path.normpath(input_path))
        output_path = f"{dir_name}_connectables.json"

    try:
        # Process directory of signalset files
        results = process_directory(input_path)

        # Write the combined results
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        total_files = len(results)
        total_connectables = sum(len(connectables) for connectables in results.values())
        print(f"Successfully processed {total_files} JSON files with a total of {total_connectables} connectables")
        print(f"Output saved to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()