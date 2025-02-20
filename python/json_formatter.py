from typing import Dict, List, Any, Optional
import json

def format_commands(commands: List[Dict[str, Any]]) -> str:
    """Format a list of commands, sorting them by header value.
    
    Args:
        commands: List of command dictionaries to format
        
    Returns:
        Formatted string with commands sorted and formatted
    """
    # Sort commands by their header value ("hdr" field)
    sorted_commands = sorted(commands, key=lambda cmd: cmd.get('hdr', ''))
    
    # Map each command through the formatter and join with commas and newlines
    formatted_commands = [format_command_json(cmd) for cmd in sorted_commands]
    commands_str = ',\n'.join(formatted_commands)
    
    # Return the final formatted string
    return f"""[
{commands_str}
]"""

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
    
    if "eax" in command:
        preamble.append(f'"eax": "{command["eax"]}"')
        
    if "tst" in command:
        preamble.append(f'"tst": "{command["tst"]}"')
        
    if "tmo" in command:
        preamble.append(f'"tmo": "{command["tmo"]}"')
        
    if command.get("fcm1", False):
        preamble.append('"fcm1": true')
        
    if command.get("dbg", False):
        preamble.append('"dbg": true')
    
    # Add command and frequency
    preamble.append(f'"cmd": {format_parameter_json(command["cmd"])}')
    preamble.append(f'"freq": {format_number(command["freq"])}')
    
    # Format signals
    # Group signals by their format.bit_offset (equivalent to format.groupId in Swift)
    signals = command.get("signals", [])
    grouped_signals = {}
    for signal in signals:
        offset = signal.get("fmt", {}).get("bix", 0)
        if offset not in grouped_signals:
            grouped_signals[offset] = []
        grouped_signals[offset].append(signal)
    
    # Sort groups by offset and format each group
    sorted_groups = sorted(grouped_signals.items(), key=lambda x: x[0])
    formatted_groups = []
    for _, group in sorted_groups:
        signal_parts = [format_signal_json(signal) for signal in group]
        formatted_groups.append(tabularize(signal_parts))
    
    scalings = ",\n".join(formatted_groups)
    
    # Return final formatted string with proper indentation
    return f"""{{ {", ".join(preamble)},
  "signals": [
{scalings}
  ]}}"""

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
    """Format enumeration signal format."""
    keys = []
    
    # Handle bit offset
    if fmt.get('bix', 0) > 0:
        keys.append(f'{{"bix": {fmt["bix"]},')
    else:
        keys.append("{")
        
    # Add bit length
    keys.append(f'"len": {fmt["len"]},')
    
    # Format map with sorted keys
    import json
    # Ensure map keys are properly sorted and formatted
    sorted_map = {str(k): v for k, v in sorted(fmt['map'].items(), key=lambda x: int(x[0]))}
    map_json = json.dumps(sorted_map)
    keys.append(f'"map": {map_json}')
    
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
    return f',\n"signalGroups": [\n{aligned_groups}\n]'

def format_number(n: float) -> str:
    """Format a number without trailing zeros after decimal point."""
    # Convert to string with high precision
    s = f"{n:.10f}"
    # Remove trailing zeros and decimal point if whole number
    s = s.rstrip('0').rstrip('.')
    return s

def format_parameter_json(param: Dict[str, str]) -> str:
    """Format a parameter dictionary (cmd field).
    
    Args:
        param: Dictionary with single key-value pair (e.g. {"21": "value"} or {"22": "value"})
        
    Returns:
        Formatted JSON string for the parameter
    """
    key = next(iter(param))
    value = param[key]
    return f'{{"{key}": "{value}"}}'

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
        output.append(format_signal_groups(data['signalGroups']))
    
    # Close the JSON object
    output.append('}')
    
    # Join all parts with appropriate newlines
    formatted = '\n'.join(output)
    
    # Write to output file if specified
    if output_path:
        with open(output_path, 'w') as f:
            f.write(formatted)
    
    return formatted
