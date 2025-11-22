"""Tests for JSON schema validation of signal definitions."""

import json
import os
import pytest
from jsonschema import validate, ValidationError

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'signals.json')


@pytest.fixture
def schema():
    """Load the signals.json schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def make_signal_data(fmt):
    """Helper to create a minimal valid signal data structure with the given fmt."""
    return {
        'commands': [{
            'hdr': '720',
            'cmd': {'22': '61A5'},
            'freq': 10,
            'signals': [{
                'id': 'TEST_SIGNAL',
                'name': 'Test Signal',
                'fmt': fmt
            }]
        }]
    }


class TestFmtFieldRequirements:
    """Test that fmt field requires either map OR (max + unit)."""

    def test_valid_with_map(self, schema):
        """Signal with map field should be valid without max/unit."""
        data = make_signal_data({
            'len': 8,
            'map': {
                '1': {'description': 'First', 'value': '1'},
                '2': {'description': 'Second', 'value': '2'}
            }
        })
        validate(data, schema)  # Should not raise

    def test_valid_with_max_and_unit(self, schema):
        """Signal with max and unit should be valid without map."""
        data = make_signal_data({
            'len': 1,
            'max': 1,
            'unit': 'offon'
        })
        validate(data, schema)  # Should not raise

    def test_valid_with_all_fields(self, schema):
        """Signal with map, max, and unit should be valid."""
        data = make_signal_data({
            'len': 8,
            'max': 255,
            'unit': 'scalar',
            'map': {
                '0': {'description': 'Off', 'value': 'off'},
                '1': {'description': 'On', 'value': 'on'}
            }
        })
        validate(data, schema)  # Should not raise

    def test_invalid_missing_both_map_and_max_unit(self, schema):
        """Signal with only len should be invalid."""
        data = make_signal_data({'len': 1})
        with pytest.raises(ValidationError) as exc_info:
            validate(data, schema)
        assert 'is not valid under any of the given schemas' in str(exc_info.value.message)

    def test_invalid_max_without_unit(self, schema):
        """Signal with max but no unit should be invalid."""
        data = make_signal_data({
            'len': 1,
            'max': 1
        })
        with pytest.raises(ValidationError) as exc_info:
            validate(data, schema)
        assert 'is not valid under any of the given schemas' in str(exc_info.value.message)

    def test_invalid_unit_without_max(self, schema):
        """Signal with unit but no max should be invalid."""
        data = make_signal_data({
            'len': 1,
            'unit': 'offon'
        })
        with pytest.raises(ValidationError) as exc_info:
            validate(data, schema)
        assert 'is not valid under any of the given schemas' in str(exc_info.value.message)


class TestFmtFieldWithOptionalFields:
    """Test fmt validation with various optional fields."""

    def test_valid_map_with_bix(self, schema):
        """Map signal with bit index should be valid."""
        data = make_signal_data({
            'bix': 8,
            'len': 4,
            'map': {
                '0': {'description': 'State A', 'value': 'A'},
                '1': {'description': 'State B', 'value': 'B'}
            }
        })
        validate(data, schema)  # Should not raise

    def test_valid_scaling_with_all_optional_fields(self, schema):
        """Scaling signal with all optional fields should be valid."""
        data = make_signal_data({
            'bix': 0,
            'len': 16,
            'max': 1000,
            'min': 0,
            'mul': 0.1,
            'div': 1,
            'add': -40,
            'sign': True,
            'unit': 'celsius',
            'nullmin': -100,
            'nullmax': 200,
            'omin': 20,
            'omax': 80,
            'oval': 50
        })
        validate(data, schema)  # Should not raise

    def test_valid_scaling_with_blsb(self, schema):
        """Scaling signal with byte LSB flag should be valid."""
        data = make_signal_data({
            'len': 16,
            'blsb': True,
            'max': 65535,
            'unit': 'scalar'
        })
        validate(data, schema)  # Should not raise


class TestRealWorldSignalExamples:
    """Test with real-world signal examples."""

    def test_gear_signal_with_map(self, schema):
        """Test gear signal example from the original request."""
        data = {
            'commands': [{
                'hdr': '7E0',
                'cmd': {'22': '1E12'},
                'freq': 2,
                'signals': [{
                    'id': 'F150_GEAR',
                    'path': 'Transmission',
                    'name': 'Gear, current',
                    'description': 'The automatic transmission gear.',
                    'fmt': {
                        'len': 8,
                        'map': {
                            '1':  {'description': 'First gear',   'value': '1'},
                            '2':  {'description': 'Second gear',  'value': '2'},
                            '3':  {'description': 'Third gear',   'value': '3'},
                            '4':  {'description': 'Fourth gear',  'value': '4'},
                            '5':  {'description': 'Fifth gear',   'value': '5'},
                            '6':  {'description': 'Sixth gear',   'value': '6'},
                            '7':  {'description': 'Seventh gear', 'value': '7'},
                            '8':  {'description': 'Eighth gear',  'value': '8'},
                            '9':  {'description': 'Ninth gear',   'value': '9'},
                            '10': {'description': 'Tenth gear',   'value': '10'}
                        }
                    }
                }]
            }]
        }
        validate(data, schema)  # Should not raise

    def test_tpms_warning_signal_with_max_unit(self, schema):
        """Test TPMS warning signal example from the original request."""
        data = {
            'commands': [{
                'hdr': '720',
                'rax': '728',
                'cmd': {'22': '61A5'},
                'freq': 10,
                'signals': [{
                    'id': 'F150_TPMS_WARN',
                    'path': 'Tires',
                    'fmt': {'bix': 2, 'len': 1, 'max': 1, 'unit': 'offon'},
                    'name': 'Tire pressure warning'
                }]
            }]
        }
        validate(data, schema)  # Should not raise

    def test_invalid_signal_missing_max_or_map(self, schema):
        """Test invalid signal missing both max and map from the original request."""
        data = {
            'commands': [{
                'hdr': '720',
                'rax': '728',
                'cmd': {'22': '61A5'},
                'freq': 10,
                'signals': [{
                    'id': 'F150_TPMS_WARN',
                    'path': 'Tires',
                    'fmt': {'len': 1},
                    'name': 'Tire pressure warning'
                }]
            }]
        }
        with pytest.raises(ValidationError):
            validate(data, schema)
