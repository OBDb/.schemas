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
from typing import Dict, Any, Optional

# Add the parent directory to the path so we can import the signalsets module
sys.path.insert(0, str(Path(__file__).parent))

from can.repo_utils import extract_make_from_repo_name

try:
    from signalsets.loader import load_signalset
except ImportError:
    print("Error: Could not import signalsets module. Make sure you're running this from the root directory.")
    sys.exit(1)


def extract_connectables(signalset_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Extract all signals with a 'suggestedMetric' or 'suggestedMetricGroup' property
    from a signalset, organizing them by filter keys derived from command filters.

    Args:
        signalset_data: The parsed JSON data of the signalset

    Returns:
        A dictionary where keys are filter strings (e.g., "<=2020", "2018<=", "2019,2020")
        and values are dictionaries mapping signal IDs to their suggestedMetric values.
        Signals from commands without filters or from signalGroups (which lack explicit filters)
        are mapped under a "ALL" key.
    """
    connectables_by_filter: Dict[str, Dict[str, str]] = {}

    def _generate_filter_key(filter_data: Optional[Dict]) -> str:
        if not filter_data:
            return "ALL"

        key_parts = []
        to_year = filter_data.get('to')
        from_year = filter_data.get('from')
        years = filter_data.get('years')  # Expected to be a list from JSON

        if to_year is not None:
            key_parts.append(f"<={to_year}")

        if from_year is not None:
            key_parts.append(f"{from_year}<=")

        if years and isinstance(years, list):
            try:
                # Ensure years are numbers and sorted for consistent key generation
                num_years = sorted([int(y) for y in years if y is not None])
                if num_years:  # Add only if there are valid years after processing
                    key_parts.append(",".join(map(str, num_years)))
            except (ValueError, TypeError):
                # If years contains non-convertible items or is not iterable as expected,
                # silently skip this part of the key.
                pass

        if not key_parts:  # Filter object existed but was empty or yielded no valid parts
            return "ALL"

        return ",".join(key_parts)

    # Process individual signals in each command
    if "commands" in signalset_data:
        for command in signalset_data.get("commands", []):  # Use .get for safety
            command_filter_data = command.get("filter")
            filter_key = _generate_filter_key(command_filter_data)

            if filter_key not in connectables_by_filter:
                connectables_by_filter[filter_key] = {}

            current_filter_connectables = connectables_by_filter[filter_key]

            if "signals" in command:
                for signal in command.get("signals", []):  # Use .get for safety
                    if "suggestedMetric" in signal and "id" in signal:
                        current_filter_connectables[signal["id"]] = signal["suggestedMetric"]

    # Process signal groups
    # These are mapped to the "NO_FILTER_APPLICABLE" key as they are assumed to lack specific filters.
    if "signalGroups" in signalset_data:
        sg_filter_key = "NO_FILTER_APPLICABLE"

        if sg_filter_key not in connectables_by_filter:
            connectables_by_filter[sg_filter_key] = {}

        current_sg_connectables = connectables_by_filter[sg_filter_key]

        for group in signalset_data.get("signalGroups", []):  # Use .get for safety
            if "suggestedMetricGroup" in group and "id" in group:
                current_sg_connectables[group["id"]] = group["suggestedMetricGroup"]

    return connectables_by_filter


def process_directory(directory_path: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Process all JSON files in a directory, extracting connectables from each.

    Args:
        directory_path: Path to the directory to scan for JSON files

    Returns:
        Dictionary mapping relative file paths to their connectables,
        where connectables are organized by filter keys.
    """
    results: Dict[str, Dict[str, Dict[str, str]]] = {}
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

                    if "commands" not in signalset_data and "signalGroups" not in signalset_data:  # Check for both
                        print(f"Skipping {file_path}: no commands or signalGroups found")
                        continue

                    # Fallback logic (simplified for brevity, assuming it remains relevant)
                    if not signalset_data.get("commands") and not signalset_data.get("signalGroups"):
                        if "-" not in root:  # Assuming root check is still valid
                            continue
                        make = extract_make_from_repo_name(file_path)
                        print(f"Falling back from {file_path} to the make repo: {make}")
                        try:
                            # This fallback path might need adjustment if it also needs to load raw JSON
                            signalset_content = load_signalset(make + '/signalsets/v3/default.json')
                            signalset_data = json.loads(signalset_content)
                        except Exception:
                            with open(file_path, 'r') as f:  # Fallback to original file if make repo fails
                                signalset_data = json.load(f)

                    # Extract connectables
                    connectables = extract_connectables(signalset_data)

                    # Only include files that have connectables
                    if connectables:  # connectables is now Dict[str_filter, Dict[str_signal, str_metric]]
                        results[rel_path] = connectables
                        # Calculate total connectables for this file based on the new structure
                        num_connectables_in_file = sum(len(v) for v in connectables.values())
                        print(f"Processed {rel_path}: found {num_connectables_in_file} connectables across {len(connectables)} filter(s)")
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
        total_connectables = sum(sum(len(v) for v in cv.values()) for cv in results.values())
        print(f"Successfully processed {total_files} JSON files with a total of {total_connectables} connectables")
        print(f"Output saved to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()