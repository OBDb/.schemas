import json
import os
import pytest

from .json_formatter import (
    tabularize,
    format_command_json,
    format_file,
    format_json_data,
    format_number,
    format_parameter_json
)

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))

def test_basic_alignment():
    rows = [
        ['{"id": "signal1",', '"path": "path1",', '"name": "name1"}'],
        ['{"id": "sig2",', '"path": "longer_path",', '"name": "name2"}']
    ]
    expected = (
        '{"id": "signal1", "path": "path1",       "name": "name1"}',
        '{"id": "sig2",    "path": "longer_path", "name": "name2"}'
    )
    result = tabularize(rows)
    assert result == ',\n'.join(expected)

def test_empty_input():
    assert tabularize([]) == ''
    assert tabularize([[]]) == ''

def test_single_row():
    rows = [['{"id": "signal1",', '"path": "path1",', '"name": "name1"}']]
    expected = '{"id": "signal1", "path": "path1", "name": "name1"}'
    assert tabularize(rows) == expected

def test_single_column():
    rows = [
        ['{"id": "signal1"}'],
        ['{"id": "signal2"}'],
        ['{"id": "signal3"}']
    ]
    expected = (
        '{"id": "signal1"}',
        '{"id": "signal2"}',
        '{"id": "signal3"}'
    )
    assert tabularize(rows) == ',\n'.join(expected)

def test_different_length_rows():
    rows = [
        ['{"id": "signal1",', '"path": "path1"'],
        ['{"id": "sig2",', '"path": "longer_path",', '"extra": "field"}']
    ]
    expected = (
        '{"id": "signal1", "path": "path1"',
        '{"id": "sig2",    "path": "longer_path", "extra": "field"}'
    )
    assert tabularize(rows) == ',\n'.join(expected)

def test_mixed_content_types():
    rows = [
        ['123', 'abc', 'xyz'],
        ['1', 'abcdef', 'x']
    ]
    expected = (
        '123 abc    xyz',
        '1   abcdef x'
    )
    assert tabularize(rows) == ',\n'.join(expected)

def test_format_number():
    assert format_number(123) == "123"
    assert format_number(123.0) == "123"
    assert format_number(123.456) == "123.456"
    assert format_number(123.45600) == "123.456"
    assert format_number(0.0) == "0"
    assert format_number(-123.456) == "-123.456"

def test_format_parameter_json():
    # Test Service 21 parameter
    param21 = {"21": "1E"}
    assert format_parameter_json(param21) == '{"21": "1E"}'

    # Test Service 22 parameter
    param22 = {"22": "404C"}
    assert format_parameter_json(param22) == '{"22": "404C"}'

    # Test uppercasing
    param22lower = {"22": "404c"}
    assert format_parameter_json(param22lower) == '{"22": "404C"}'

    # Test AT command parameter
    param_at = {"AT": "Z"}
    assert format_parameter_json(param_at) == '{"AT": "Z"}'

def test_format_command_json():
    basic_command = {
        "hdr": "720",
        "rax": "728",
        "cmd": {"22": "404C"},
        "freq": 5,
        "signals": [
            {
                "id": "F150_ODO",
                "path": "Trips",
                "fmt": {
                    "len": 24,
                    "max": 1677721,
                    "div": 10,
                    "unit": "kilometers"
                },
                "name": "Odometer",
                "suggestedMetric": "odometer"
            }
        ]
    }

    result = format_command_json(basic_command)
    assert result == """
{ "hdr": "720", "rax": "728", "cmd": {"22": "404C"}, "freq": 5,
  "signals": [
    {"id": "F150_ODO", "path": "Trips", "fmt": { "len": 24, "max": 1677721, "div": 10, "unit": "kilometers" }, "name": "Odometer", "suggestedMetric": "odometer"}
  ]}
""".strip()

def test_format_command_with_optional_fields():
    command_with_options = {
        "hdr": "720",
        "rax": "728",
        "eax": "F1",
        "tst": "01",
        "tmo": "32",
        "fcm1": True,
        "dbg": True,
        "cmd": {"22": "404C"},
        "freq": 5,
        "signals": []
    }

    result = format_command_json(command_with_options)
    assert result == """
{ "hdr": "720", "rax": "728", "eax": "F1", "tst": "01", "tmo": "32", "fcm1": true, "dbg": true, "cmd": {"22": "404C"}, "freq": 5,
  "signals": [
  ]}
""".strip()

def test_strips_duplicate_commands():
    with_duplicates = """
{ "commands": [
{ "hdr": "7E0", "rax": "7E8", "cmd": {"22": "1E12"}, "freq": 2,
  "signals": [
    {"id": "F150_GEAR", "path": "Engine", "name": "Current gear", "description": "The automatic transmission gear.", "fmt": {"len": 8, "map": {
          "1":  { "description": "First gear",   "value": "1" },
          "2":  { "description": "Second gear",  "value": "2" },
          "3":  { "description": "Third gear",   "value": "3" },
          "4":  { "description": "Fourth gear",  "value": "4" },
          "5":  { "description": "Fifth gear",   "value": "5" },
          "6":  { "description": "Sixth gear",   "value": "6" },
          "7":  { "description": "Seventh gear", "value": "7" },
          "8":  { "description": "Eighth gear",  "value": "8" },
          "9":  { "description": "Ninth gear",   "value": "9" },
          "10": { "description": "Tenth gear",   "value": "10" }
        }}
    }
  ]},
{ "hdr": "7E0", "rax": "7E8", "cmd": {"22": "1E12"}, "freq": 2,
  "signals": [
    {"id": "F150_GEAR", "path": "Engine", "fmt": { "len": 8, "map": {"1":{"description":"First gear","value":"1"},"10":{"description":"Manual","value":"MANUAL"},"2":{"description":"Second gear","value":"2"},"3":{"description":"Third gear","value":"3"},"4":{"description":"Fourth gear","value":"4"},"46":{"description":"Drive","value":"DRIVE"},"5":{"description":"Fifth gear","value":"5"},"50":{"description":"Neutral","value":"NEUTRAL"},"6":{"description":"Sixth gear","value":"6"},"60":{"description":"Reverse","value":"REVERSE"},"7":{"description":"Seventh gear","value":"7"},"70":{"description":"Park","value":"PARK"},"8":{"description":"Eighth gear","value":"8"},"9":{"description":"Ninth gear","value":"9"}} }, "name": "Current gear", "description": "The automatic transmission gear."}
  ]}
]
}
"""

    result = format_json_data(json.loads(with_duplicates))
    assert result == """{ "commands": [
{ "hdr": "7E0", "rax": "7E8", "cmd": {"22": "1E12"}, "freq": 2,
  "signals": [
    {"id": "F150_GEAR", "path": "Engine", "name": "Current gear", "description": "The automatic transmission gear.", "fmt": {"len": 8, "map": {
          "1":  { "description": "First gear",   "value": "1" },
          "2":  { "description": "Second gear",  "value": "2" },
          "3":  { "description": "Third gear",   "value": "3" },
          "4":  { "description": "Fourth gear",  "value": "4" },
          "5":  { "description": "Fifth gear",   "value": "5" },
          "6":  { "description": "Sixth gear",   "value": "6" },
          "7":  { "description": "Seventh gear", "value": "7" },
          "8":  { "description": "Eighth gear",  "value": "8" },
          "9":  { "description": "Ninth gear",   "value": "9" },
          "10": { "description": "Tenth gear",   "value": "10" }
        }}
    }
  ]}
]
}
"""

@pytest.mark.parametrize("test_file", [
    "ford-f-150.json",
    "saej1979.json",
    "porsche-taycan.json",
    "porsche-macan-electric.json"
], ids=lambda x: x.split('.')[0].replace('-', '_'))  # Create readable test IDs
def test_signal_formatting(test_file):
    """Test signal set formatting for various vehicle models."""
    signalset_path = os.path.join(REPO_ROOT, 'testdata', test_file)

    formatted = format_file(signalset_path)

    with open(signalset_path) as f:
        assert f.read() == formatted

def test_format_command_signals_sorted_by_bix():
    """Test that signals are sorted by their bix value with default of 0 when not provided."""
    command_with_mixed_bix = {
        "hdr": "720",
        "rax": "728",
        "cmd": {"22": "404C"},
        "freq": 5,
        "signals": [
            # Signal with bix=5
            {
                "id": "SIGNAL_BIX_5",
                "fmt": {
                    "bix": 5,
                    "len": 8,
                    "max": 100,
                    "unit": "km/h"
                },
                "name": "Signal with bix 5"
            },
            # Signal with no bix (defaults to 0)
            {
                "id": "SIGNAL_NO_BIX",
                "fmt": {
                    "len": 16,
                    "max": 1000,
                    "unit": "rpm"
                },
                "name": "Signal with no bix"
            },
            # Signal with bix=2
            {
                "id": "SIGNAL_BIX_2",
                "fmt": {
                    "bix": 2,
                    "len": 10,
                    "max": 50,
                    "unit": "celsius"
                },
                "name": "Signal with bix 2"
            },
            # Enum signal with bix=1
            {
                "id": "SIGNAL_ENUM_BIX_1",
                "fmt": {
                    "bix": 1,
                    "len": 4,
                    "map": {
                        "0": "Off",
                        "1": "On"
                    }
                },
                "name": "Enum signal with bix 1"
            },
            # Enum signal with bix=10
            {
                "id": "SIGNAL_ENUM_BIX_10",
                "fmt": {
                    "bix": 10,
                    "len": 2,
                    "map": {
                        "0": "Low",
                        "1": "Medium",
                        "2": "High"
                    }
                },
                "name": "Enum signal with bix 10"
            }
        ]
    }

    result = format_command_json(command_with_mixed_bix)

    # Extract the signal IDs in the order they appear in the formatted result
    signal_order = []
    for line in result.split('\n'):
        if '"id": "' in line:
            id_start = line.find('"id": "') + 7
            id_end = line.find('"', id_start)
            signal_id = line[id_start:id_end]
            signal_order.append(signal_id)

    expected_order = [
        "SIGNAL_NO_BIX",      # bix=0 (default)
        "SIGNAL_BIX_2",       # bix=2
        "SIGNAL_BIX_5",       # bix=5
        "SIGNAL_ENUM_BIX_1",  # bix=1 (maps are placed at the end)
        "SIGNAL_ENUM_BIX_10"  # bix=10
    ]

    assert signal_order == expected_order, f"Signals not sorted by bix. Got: {signal_order}, Expected: {expected_order}"


if __name__ == '__main__':
    pytest.main([__file__])
