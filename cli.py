#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from python.json_formatter import format_file
from python.ecu_entries import describe_entry, find_ecu_conflicts


def report_ecu_conflicts(input_file: str) -> bool:
    """Print ECU entries that name different types for one command and year."""
    with open(input_file) as f:
        entries = json.load(f).get('ecu', [])
    conflicts = find_ecu_conflicts(entries)
    for conflict in conflicts:
        print(
            f"✗ ECU entry {describe_entry(conflict['entry'])} conflicts with "
            f"{describe_entry(conflict['conflicting_entry'])} in model year {conflict['year']}",
            file=sys.stderr
        )
    return bool(conflicts)

def main():
    parser = argparse.ArgumentParser(
        description='Format signal set JSON files in a compact, column-aligned way'
    )
    parser.add_argument(
        'input_file',
        type=str,
        help='Path to input JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Path to output file. If not specified, prints to stdout',
        default=None
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if file is properly formatted without modifying it'
    )

    args = parser.parse_args()

    # Verify input file exists
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        sys.exit(1)

    try:
        if args.check:
            # Read current file content
            with open(input_path, 'r') as f:
                current_content = f.read()

            # Get formatted content (with overlap checking)
            formatted_content, overlaps = format_file(str(input_path), return_overlaps=True)

            # Compare and exit with appropriate status
            if current_content.strip() == formatted_content.strip():
                print(f"✓ {args.input_file} is properly formatted")
            else:
                print(f"✗ {args.input_file} needs reformatting", file=sys.stderr)
                sys.exit(1)

            ecu_conflicted = report_ecu_conflicts(args.input_file)

            # Report overlapping signals as error
            if overlaps:
                for err in overlaps:
                    print(
                        f"✗ Signal '{err['signal_id']}' overlaps with '{err['conflicting_signal_id']}' "
                        f"at bit {err['bit']} in command [{err['command']}]",
                        file=sys.stderr
                    )
                sys.exit(1)

            if ecu_conflicted:
                sys.exit(1)
        else:
            # Format the file (with overlap checking, write first then check)
            formatted_content, overlaps = format_file(args.input_file, args.output, return_overlaps=True)

            if args.output:
                print(f"Formatted {args.input_file} -> {args.output}")
            else:
                print(formatted_content)

            ecu_conflicted = report_ecu_conflicts(args.input_file)

            # Report overlapping signals as error after writing
            if overlaps:
                for err in overlaps:
                    print(
                        f"✗ Signal '{err['signal_id']}' overlaps with '{err['conflicting_signal_id']}' "
                        f"at bit {err['bit']} in command [{err['command']}]",
                        file=sys.stderr
                    )
                sys.exit(1)

            if ecu_conflicted:
                sys.exit(1)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
