import json
import os

import pytest
from jsonschema import ValidationError, validate

from .ecu_entries import filter_matches, find_ecu_conflicts, specificity
from .json_formatter import format_json_data

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'signals.json')

COMMAND = {
    'hdr': '7E0',
    'cmd': {'22': 'F40D'},
    'freq': 1,
    'signals': [{'id': 'X', 'path': 'Engine', 'name': 'X', 'fmt': {'len': 8, 'max': 255, 'unit': 'scalar'}}],
}


@pytest.fixture
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def test_schema_accepts_each_entry_form(schema):
    validate({'ecu': [
        {'hdr': '7E0', 'type': 'engine'},
        {'hdr': '6F1', 'eax': '12', 'type': 'engine'},
        {'hdr': 'FC00', 'rax': 'FE0076', 'type': 'engine'},
        {'hdr': '7E4', 'filter': {'from': 2012, 'to': 2018}, 'type': 'battery'},
    ], 'commands': [COMMAND]}, schema)


def test_schema_rejects_unknown_type(schema):
    with pytest.raises(ValidationError):
        validate({'ecu': [{'hdr': '7E0', 'type': 'fluxCapacitor'}], 'commands': [COMMAND]}, schema)


def test_schema_requires_hdr_and_type(schema):
    with pytest.raises(ValidationError):
        validate({'ecu': [{'type': 'engine'}], 'commands': [COMMAND]}, schema)
    with pytest.raises(ValidationError):
        validate({'ecu': [{'hdr': '7E0'}], 'commands': [COMMAND]}, schema)


def test_filter_matches_like_the_app():
    assert filter_matches(None, 1999)
    assert filter_matches({}, 1999)
    assert filter_matches({'from': 2012, 'to': 2018}, 2015)
    assert not filter_matches({'from': 2012, 'to': 2018}, 2019)
    assert filter_matches({'to': 2012, 'from': 2018}, 2019)
    assert not filter_matches({'to': 2012, 'from': 2018}, 2015)
    assert filter_matches({'from': 2020}, 2020)
    assert filter_matches({'to': 2010, 'years': [2015]}, 2015)
    assert not filter_matches({'years': [2015]}, 2016)


def test_specificity_counts_optional_fields():
    assert specificity({'hdr': '7E0', 'type': 'engine'}) == 0
    assert specificity({'hdr': '6F1', 'eax': '12', 'rax': '612', 'filter': {'from': 2020}, 'type': 'engine'}) == 3


def test_a_narrower_entry_overrides_without_conflict():
    assert find_ecu_conflicts([
        {'hdr': '7E4', 'type': 'engine'},
        {'hdr': '7E4', 'filter': {'from': 2012, 'to': 2018}, 'type': 'battery'},
    ]) == []


def test_entries_for_different_addresses_do_not_conflict():
    assert find_ecu_conflicts([
        {'hdr': '6F1', 'eax': '12', 'type': 'engine'},
        {'hdr': '6F1', 'eax': '18', 'type': 'transmission'},
        {'hdr': '7E0', 'type': 'engine'},
        {'hdr': '7E1', 'type': 'transmission'},
    ]) == []


def test_disjoint_years_do_not_conflict():
    assert find_ecu_conflicts([
        {'hdr': '7E4', 'filter': {'to': 2018}, 'type': 'battery'},
        {'hdr': '7E4', 'filter': {'from': 2019}, 'type': 'charger'},
    ]) == []


def test_overlapping_years_conflict():
    conflicts = find_ecu_conflicts([
        {'hdr': '7E4', 'filter': {'to': 2018}, 'type': 'battery'},
        {'hdr': '7E4', 'filter': {'from': 2018}, 'type': 'charger'},
    ])
    assert len(conflicts) == 1
    assert conflicts[0]['year'] == 2018


def test_eax_and_rax_entries_can_both_match_one_command():
    assert len(find_ecu_conflicts([
        {'hdr': '6F1', 'eax': '12', 'type': 'engine'},
        {'hdr': '6F1', 'rax': '612', 'type': 'transmission'},
    ])) == 1


def test_formatter_sorts_and_aligns_entries():
    formatted = format_json_data({'ecu': [
        {'hdr': '7E4', 'filter': {'from': 2012, 'to': 2018}, 'type': 'battery'},
        {'hdr': '7E0', 'type': 'engine'},
        {'hdr': '6F1', 'eax': '12', 'type': 'engine'},
    ], 'commands': [COMMAND]})
    assert formatted.startswith(
        '{ "ecu": [\n'
        '    { "hdr": "6F1", "eax": "12",                                         "type": "engine" },\n'
        '    { "hdr": "7E0",                                                      "type": "engine" },\n'
        '    { "hdr": "7E4",              "filter": { "from": 2012, "to": 2018 }, "type": "battery" }\n'
        '  ],\n'
        '  "commands": [\n'
    )


def test_formatter_round_trips_ecu_with_diagnostic_level():
    data = {'ecu': [{'hdr': '7E0', 'type': 'engine'}], 'diagnosticLevel': 'C0', 'commands': [COMMAND]}
    formatted = format_json_data(data)
    assert json.loads(formatted)['ecu'] == data['ecu']
    assert json.loads(formatted)['diagnosticLevel'] == 'C0'
    assert format_json_data(json.loads(formatted)) == formatted


def test_formatter_leaves_signalsets_without_ecu_unchanged():
    assert format_json_data({'commands': [COMMAND]}).startswith('{ "commands": [\n')
    assert format_json_data({'ecu': [], 'commands': [COMMAND]}).startswith('{ "commands": [\n')
