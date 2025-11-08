from typing import Dict, List, Any, Optional
import json

def format_commands(commands: List[Dict[str, Any]]) -> str:
    """Format a list of commands, sorting them by cmd parameter ID and removing duplicates.

    Args:
        commands: List of command dictionaries to format

    Returns:
        Formatted string with unique commands sorted and formatted
    """
    # Remove duplicates before sorting
    unique_commands = remove_duplicate_commands(commands)

    # Sort commands by their cmd parameter ID
    sorted_commands = sorted(unique_commands, key=get_command_sort_key)

    # Map each command through the formatter and join with commas and newlines
    formatted_commands = [format_command_json(cmd) for cmd in sorted_commands]
    commands_str = ',\n'.join(formatted_commands)

    # Return the final formatted string
    return f"""[
{commands_str}
]"""

def get_command_sort_key(cmd: Dict[str, Any]) -> tuple:
    """Create a sort key for a command based on hdr, rax, and cmd parameters.

    Args:
        cmd: Command dictionary

    Returns:
        Tuple containing header, receive address, service type and parameter ID for sorting
    """
    # Get the protocol value
    proto = cmd.get('proto', '')

    # Get the header (hdr) value
    hdr = cmd.get('hdr', '')

    # Get the receive address (rax) value
    rax = cmd.get('rax', '')

    # Get cmd parameter details
    cmd_param = cmd.get('cmd', {})
    service_type = next(iter(cmd_param.keys()), '')
    param_id = cmd_param.get(service_type, '')

    # Convert parameter ID to integer for proper numeric sorting
    # Handle both decimal and hex values
    try:
        if isinstance(param_id, str):
            param_id_int = int(param_id, 16)
        else:
            param_id_int = int(param_id)
    except (ValueError, TypeError):
        param_id_int = 0  # Default if conversion fails

    return (proto, hdr, rax, service_type, param_id_int)

def get_command_signature(cmd: Dict[str, Any]) -> tuple:
    """Create a unique signature for a command based on all fields except signals.

    Args:
        cmd: Command dictionary

    Returns:
        Tuple containing all relevant fields that define uniqueness
    """
    return (
        cmd.get('hdr'),
        cmd.get('rax'),
        json.dumps(cmd.get('cmd')),     # Convert dict to stable string representation
        json.dumps(cmd.get('filter'))   # Convert dict to stable string representation
    )

def remove_duplicate_commands(commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate commands based on their full configuration (excluding signals).

    Args:
        commands: List of command dictionaries

    Returns:
        List of commands with duplicates removed, keeping the first occurrence
    """
    seen_signatures = set()
    unique_commands = []

    for cmd in commands:
        signature = get_command_signature(cmd)
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_commands.append(cmd)

    return unique_commands

def format_filter_json(filter_obj: Dict[str, Any]) -> str:
    """Format a filter object into a single line JSON string.

    Args:
        filter_obj: Dictionary containing filter data (from, to, years)

    Returns:
        Formatted JSON string for the filter object
    """
    parts = []

    # Get values for ordering logic
    from_val = filter_obj.get("from")
    to_val = filter_obj.get("to")
    years_val = filter_obj.get("years", [])

    # Sort years for consistent output
    sorted_years = sorted(list(years_val)) if years_val else []
    max_year = max(sorted_years) if sorted_years else None

    # Determine if from should be placed after to and/or years
    from_after_to = from_val is not None and to_val is not None and from_val > to_val
    from_after_years = from_val is not None and max_year is not None and from_val > max_year

    # Add fields in chronological order
    if "from" in filter_obj and not from_after_to and not from_after_years:
        parts.append(f'"from": {filter_obj["from"]}')

    if "to" in filter_obj:
        parts.append(f'"to": {filter_obj["to"]}')

    if "from" in filter_obj and from_after_to and not from_after_years:
        parts.append(f'"from": {filter_obj["from"]}')

    if "years" in filter_obj and filter_obj["years"]:
        parts.append(f'"years": {json.dumps(sorted_years)}')

    if "from" in filter_obj and from_after_years:
        parts.append(f'"from": {filter_obj["from"]}')

    return f'{{ {", ".join(parts)} }}'

def format_command_json(command: Dict[str, Any]) -> str:
    """Format a command dictionary in a human-friendly way.

    Args:
        command: Dictionary containing command data

    Returns:
        Formatted JSON string for the command
    """
    # Start building preamble with required hdr field
    preamble = [
        f'"hdr": "{command["hdr"]}"'
    ]

    # Add optional fields if present
    if "rax" in command:
        preamble.append(f'"rax": "{command["rax"]}"')

    if "proto" in command:
        preamble.append(f'"proto": "{command["proto"]}"')

    if "eax" in command:
        preamble.append(f'"eax": "{command["eax"]}"')

    if "pri" in command:
        preamble.append(f'"pri": "{command["pri"]}"')

    if "tst" in command:
        preamble.append(f'"tst": "{command["tst"]}"')

    if "tmo" in command:
        preamble.append(f'"tmo": "{command["tmo"]}"')

    if command.get("fcm1", False):
        preamble.append('"fcm1": true')

    if "din" in command:
        preamble.append(f'"din": "{command["din"]}"')

    if "dout" in command:
        preamble.append(f'"dout": "{command["dout"]}"')

    if command.get("dbg", False):
        preamble.append('"dbg": true')

    # Add command and frequency
    preamble.append(f'"cmd": {format_parameter_json(command["cmd"])}')
    preamble.append(f'"freq": {format_number(command["freq"])}')

    if "filter" in command:
        preamble.append(f'"filter": {format_filter_json(command["filter"])}')

    if "dbgfilter" in command:
        preamble.append(f'"dbgfilter": {format_filter_json(command["dbgfilter"])}')

    # Separate signals into scalings and enumerations
    signals = command.get("signals", [])

    # Sort signals by bix value (default 0 if not present)
    sorted_signals = sorted(signals, key=lambda s: s.get("fmt", {}).get("bix", 0))

    scaling_signals = []
    enum_signals = []

    for signal in sorted_signals:
        if 'map' in signal.get('fmt', {}):
            enum_signals.append(signal)
        else:
            scaling_signals.append(signal)

    # Build the signals section
    signals_lines = ['  "signals": [']

    # Format scaling signals (if any) using tabularization
    if scaling_signals:
        signal_parts = [format_scaling_signal_json(signal) for signal in scaling_signals]
        tabularized = tabularize(signal_parts)
        if tabularized:
            signals_lines.extend(['    ' + line for line in tabularized.split('\n')])

    # Add enumeration signals (if any)
    if enum_signals:
        # Add comma after scaling signals if needed
        if scaling_signals and signals_lines[-1][-1] != ',':
            signals_lines[-1] += ','

        # Format each enumeration signal
        for i, signal in enumerate(enum_signals):
            enum_lines = format_enum_signal_json(signal)

            # Add comma if not the last signal
            if i < len(enum_signals) - 1:
                enum_lines[-1] += ','

            signals_lines.extend(['    ' + line for line in enum_lines])

    signals_lines.append('  ]')

    # Combine all parts
    return f"""{{ {", ".join(preamble)},
{chr(10).join(signals_lines)}}}"""

def format_scaling_signal_json(signal: Dict[str, Any]) -> List[str]:
    """Format a scaling signal for tabularization."""
    result = [f'{{"id": "{signal["id"]}",']

    if "path" in signal:
        result.append(f'"path": "{signal["path"]}",')

    result.append('"fmt":')

    # Format scaling
    result.extend(_format_scaling(signal["fmt"]))

    # Add name and optional fields
    result.append(f'"name": "{signal["name"]}"')

    if "suggestedMetric" in signal:
        result[-1] += ","
        result.append(f'"suggestedMetric": "{signal["suggestedMetric"]}"')

    if description := signal.get("description"):
        result[-1] += ","
        result.append(f'"description": "{description}"')

    if signal.get("hidden", False):
        result[-1] += ","
        result.append('"hidden": true')

    result[-1] += "}"

    return result

def format_enum_signal_json(signal: Dict[str, Any]) -> List[str]:
    """Format an enumeration signal with column-aligned map values.

    Args:
        signal: Dictionary containing signal data including enumeration mapping

    Returns:
        List of strings representing the formatted enumeration signal
    """
    lines = []

    # Start signal object with id, path, name, description, and fmt opening
    opening_line = '{'
    opening_line += f'"id": "{signal["id"]}"'

    if "path" in signal:
        opening_line += f', "path": "{signal["path"]}"'

    opening_line += f', "name": "{signal["name"]}"'

    if description := signal.get("description"):
        opening_line += f', "description": "{description}"'

    if "suggestedMetric" in signal:
        opening_line += f', "suggestedMetric": "{signal["suggestedMetric"]}"'

    if signal.get("hidden", False):
        opening_line += ', "hidden": true'

    opening_line += f', "fmt": {{'

    # Handle bit offset if present
    if 'bix' in signal['fmt']:
        opening_line += f'"bix": {signal["fmt"]["bix"]}, '

    opening_line += f'"len": {signal["fmt"]["len"]}, "map": {{'
    lines.append(opening_line)

    # Prepare map entries for tabularization
    map_rows = []
    map_items = sorted(signal["fmt"]["map"].items(), key=lambda x: int(x[0]))

    for key, value in map_items:
        if isinstance(value, dict):
            description = value.get('description', '')
            value_str = value.get('value', '')
        else:
            description = str(value)
            value_str = str(value)

        row = [
            f'      "{key}":',
            '{',
            f'"description": "{description}",',
            f'"value": "{value_str}"' + ' }',
        ]
        map_rows.append(row)

    # Tabularize the map entries
    tabularized_map = tabularize(map_rows)
    if tabularized_map:
        lines.extend(tabularized_map.split('\n'))

    # Close map and format sections
    lines.append('    }}')
    lines.append('}')

    return lines

def format_signal_json(signal: Dict[str, Any]) -> List[str]:
    """Format a signal dictionary into a list of strings for tabular formatting.

    Args:
        signal: Dictionary containing signal data including:
            - id: Signal identifier
            - name: Signal name
            - path: Optional navigation path
            - fmt: Format specification (either enumeration or scaling)
            - suggestedMetric: Optional metric suggestion
            - description: Optional signal description
            - hidden: Optional boolean flag

    Returns:
        List of strings representing the formatted signal parts for tabular alignment
    """
    # Start with opening brace and ID
    result = [f'    {{"id": "{signal["id"]}",']

    # Add path if present
    if "path" in signal:
        result.append(f'"path": "{signal["path"]}",')

    # Add format field marker
    result.append('"fmt":')

    # Format the format specification (enumeration or scaling)
    result.extend(format_signal_format(signal["fmt"]))

    # Add required name field
    result.append(f'"name": "{signal["name"]}"')

    # Handle optional fields, adding commas to previous line as needed

    # Add suggested metric if present
    if "suggestedMetric" in signal:
        result[-1] += ","  # Add comma to previous line
        result.append(f'"suggestedMetric": "{signal["suggestedMetric"]}"')

    # Add description if present and non-empty
    if description := signal.get("description"):
        result[-1] += ","  # Add comma to previous line
        result.append(f'"description": "{description}"')

    # Add hidden flag if true
    if signal.get("hidden", False):
        result[-1] += ","  # Add comma to previous line
        result.append('"hidden": true')

    # Close the signal object
    result[-1] += "}"

    return result

def format_signal_format(fmt: dict) -> list[str]:
    """Format a signal format dictionary into list of strings for tabular formatting.

    Args:
        fmt: Dictionary containing either enumeration or scaling format data

    Returns:
        List of strings representing the formatted format parts
    """
    # Determine if this is an enumeration or scaling format
    if 'map' in fmt:
        return _format_enumeration(fmt)
    else:
        return _format_scaling(fmt)

def _format_enumeration(fmt: dict) -> list[str]:
    """Format enumeration signal format with multi-line map values.

    Args:
        fmt: Dictionary containing enumeration format data

    Returns:
        List of strings representing the formatted enumeration parts
    """
    keys = []

    # Handle bit offset
    if fmt.get('bix', 0) > 0:
        keys.append(f'{{"bix": {fmt["bix"]},')
    else:
        keys.append("{")

    # Add bit length
    keys.append(f'"len": {fmt["len"]},')

    # Format map with each value on its own line
    map_items = []
    sorted_items = sorted(fmt['map'].items(), key=lambda x: int(x[0]))

    # Start map object
    map_lines = ['"map": {']

    # Format each map entry
    for key, value in sorted_items:
        # Handle both dictionary and string value formats
        if isinstance(value, dict):
            description = value.get('description', '')
            value_str = value.get('value', '')
            map_lines.append(f'      "{key}": {{"description": "{description}", "value": "{value_str}"}},')
        else:
            # For simple string values, use the value as both description and value
            map_lines.append(f'      "{key}": {{"description": "{value}", "value": "{value}"}},')

    # Remove trailing comma from last entry
    if map_lines[-1].endswith(','):
        map_lines[-1] = map_lines[-1][:-1]

    # Close map object
    map_lines.append('    }')

    # Add formatted map to keys
    keys.extend(map_lines)

    # Close the format object
    keys.append("},")

    return keys

def _format_scaling(fmt: dict) -> list[str]:
    """Format scaling signal format."""
    keys = []

    # Handle bit offset
    if fmt.get('bix', 0) > 0:
        keys.append(f'{{"bix": {fmt["bix"]},')
    else:
        keys.append("{")

    # Add bit length
    keys.append(f'"len": {fmt["len"]},')

    # Add bytes LSB if true
    if fmt.get('blsb', False):
        keys.append('"blsb": true,')

    # Add max value
    keys.append(f'"max": {format_number(fmt["max"])},')

    # Add optional fields, using empty string for missing/default values
    if fmt.get('min', 0) != 0:
        keys.append(f'"min": {format_number(fmt["min"])},')
    else:
        keys.append("")

    if fmt.get('mul', 1) != 1:
        keys.append(f'"mul": {format_number(fmt["mul"])},')
    else:
        keys.append("")

    if fmt.get('div', 1) != 1:
        keys.append(f'"div": {format_number(fmt["div"])},')
    else:
        keys.append("")

    if fmt.get('add', 0) != 0:
        keys.append(f'"add": {format_number(fmt["add"])},')
    else:
        keys.append("")

    if fmt.get('sign', False):
        keys.append('"sign": true,')
    else:
        keys.append("")

    if 'nullmin' in fmt:
        keys.append(f'"nullmin": {format_number(fmt["nullmin"])},')
    else:
        keys.append("")

    if 'nullmax' in fmt:
        keys.append(f'"nullmax": {format_number(fmt["nullmax"])},')
    else:
        keys.append("")

    # Add unit and close format object
    keys.append(f'"unit": "{fmt["unit"]}"')
    keys.append("},")

    return keys

def format_number(n: float) -> str:
    """Format a number without trailing zeros after decimal point."""
    # Convert to string with high precision
    s = f"{n:.10f}"
    # Remove trailing zeros and decimal point if whole number
    s = s.rstrip('0').rstrip('.')
    return s

def format_signal_groups(groups: List[Dict[str, Any]]) -> str:
    """Format signal groups in a human-friendly way.

    Args:
        groups: List of signal group dictionaries to format

    Returns:
        Formatted string with signal groups sorted and formatted
    """
    if not groups:
        return ''

    # Sort groups by their ID
    sorted_groups = sorted(groups, key=lambda g: g['id'])

    formatted_rows = []
    for group in sorted_groups:
        row_parts = []

        # Start with ID
        row_parts.append(f'  {{"id": "{group["id"]}",')

        # Add navigation path if present
        if navigation_path := group.get('path'):
            row_parts.append(f'"path": "{navigation_path}",')

        # Add matching regex, escaping backslashes
        matching_regex = group['matchingRegex'].replace('\\', '\\\\')
        row_parts.append(f'"matchingRegex": "{matching_regex}",')

        if "filter" in group:
            row_parts.append(f'"filter": {format_filter_json(group["filter"])}')

        if "dbgfilter" in group:
            row_parts.append(f'"dbgfilter": {format_filter_json(group["dbgfilter"])}')

        # Add required name
        row_parts.append(f'"name": "{group["name"]}"')

        # Add suggested metric group if present
        if suggested_metric_group := group.get('suggestedMetricGroup'):
            row_parts[-1] += ','  # Add comma to previous part
            row_parts.append(f'"suggestedMetricGroup": "{suggested_metric_group}"')

        # Close the group object
        row_parts[-1] += '}'

        formatted_rows.append(row_parts)

    # Use tabularize to align the columns
    aligned_groups = tabularize(formatted_rows)

    # Return the formatted string with proper comma and newlines
    return f'"signalGroups": [\n{aligned_groups}\n]'

def format_number(n: float) -> str:
    """Format a number without trailing zeros after decimal point."""
    # Convert to string with high precision
    s = f"{n:.10f}"
    # Remove trailing zeros and decimal point if whole number
    s = s.rstrip('0').rstrip('.')
    return s

def format_parameter_json(param: Dict[str, str]) -> str:
    """Format a parameter dictionary (cmd field) with uppercase hex values.

    Args:
        param: Dictionary with single key-value pair (e.g. {"21": "value"} or {"22": "value"})

    Returns:
        Formatted JSON string for the parameter with uppercase hex values
    """
    key = next(iter(param))
    value = param[key]

    return f'{{"{key}": "{value.upper()}"}}'

def tabularize(rows: list[list[str]]) -> str:
    """
    Aligns columns in a list of string lists and joins them with commas and newlines.

    Args:
        rows: List of lists of strings, where each inner list represents a row

    Returns:
        String with aligned columns, rows separated by commas and newlines
    """
    # Calculate maximum length for each column
    max_lengths = {}
    for row in rows:
        for index, column in enumerate(row):
            max_lengths[index] = max(max_lengths.get(index, 0), len(column))

    # Process each row
    formatted_rows = []
    for row in rows:
        # Process each column in the row
        formatted_columns = []
        for index, column in enumerate(row):
            max_length = max_lengths.get(index)
            if max_length and max_length > 0:
                # Add padding if not the last column
                if index < len(row) - 1:
                    padding = ' ' * (max_length - len(column) + 1)
                    formatted_columns.append(column + padding)
                else:
                    formatted_columns.append(column)

        # Join columns for this row
        formatted_rows.append(''.join(formatted_columns))

    # Join all rows with comma and newline
    return ',\n'.join(formatted_rows)

def format_json_data(data) -> str:
    # Start building the formatted output
    output = []

    # Handle diagnostic level if present
    if 'diagnosticLevel' in data:
        output.append('{ "diagnosticLevel": "' + data['diagnosticLevel'] + '",')
        output.append('  "commands": ' + format_commands(data['commands']))
    else:
        output.append('{ "commands": ' + format_commands(data['commands']))

    # Handle signal groups if present
    if 'signalGroups' in data:
        output[-1] += ','
        output.append(format_signal_groups(data['signalGroups']))

    # Handle synthetics if present
    if 'synthetics' in data:
        output[-1] += ','
        output.append(format_synthetics(data['synthetics']))

    # Close the JSON object
    output.append('}')

    # Join all parts with appropriate newlines
    formatted = '\n'.join(output) + '\n'

    return formatted

def format_file(input_path: str, output_path: Optional[str] = None) -> str:
    """Format a signal set JSON file in a human-friendly way.

    Args:
        input_path: Path to input JSON file
        output_path: Optional path to output file. If not specified, returns formatted string

    Returns:
        Formatted JSON string
    """
    # Read and parse input JSON
    with open(input_path, 'r') as f:
        data = json.load(f)

    formatted = format_json_data(data)

    # Write to output file if specified
    if output_path:
        with open(output_path, 'w') as f:
            f.write(formatted)

    return formatted

def format_synthetics(synthetics: List[Dict[str, Any]]) -> str:
    """Format synthetic signals in a human-friendly way.

    Args:
        synthetics: List of synthetic signal dictionaries to format

    Returns:
        Formatted string with synthetic signals
    """
    if not synthetics:
        return ''

    # Sort synthetics by their ID
    sorted_synthetics = sorted(synthetics, key=lambda s: s['id'])

    # Format each synthetic signal
    formatted_synthetics = []
    for synthetic in sorted_synthetics:
        # Start with ID
        parts = [f'  {{ "id": "{synthetic["id"]}"']

        # Add required fields
        parts.append(f', "path": "{synthetic["path"]}"')
        parts.append(f', "name": "{synthetic["name"]}"')

        # Add optional fields
        if "max" in synthetic:
            parts.append(f', "max": {format_number(synthetic["max"])}')

        if "min" in synthetic:
            parts.append(f', "min": {format_number(synthetic["min"])}')

        parts.append(f', "unit": "{synthetic["unit"]}"')

        if "suggestedMetric" in synthetic:
            parts.append(f', "suggestedMetric": "{synthetic["suggestedMetric"]}"')

        # Format formula
        formula = synthetic["formula"]
        formula_parts = []
        formula_parts.append('"op": "' + formula["op"] + '"')
        formula_parts.append('"a": "' + formula["a"] + '"')
        formula_parts.append('"b": "' + formula["b"] + '"')

        parts.append(', "formula": {')
        parts.append('\n    ' + ', '.join(formula_parts))
        parts.append('\n  }}')

        formatted_synthetics.append(''.join(parts))

    # Join all formatted synthetics with commas and newlines
    synthetics_str = ',\n'.join(formatted_synthetics)

    # Return the final formatted string
    return f'"synthetics": [\n{synthetics_str}\n]'
