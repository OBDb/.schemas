import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'signals.json').read_text())


@pytest.mark.parametrize('definition', [
    SCHEMA['definitions']['suggestedMetricEnum'],
    SCHEMA['properties']['signalGroups']['items']['properties']['suggestedMetricGroup'],
])
def test_every_metric_has_one_description(definition):
    assert [option['const'] for option in definition['oneOf']] == definition['enum']
    assert all(option['description'].strip() for option in definition['oneOf'])
    validator = Draft7Validator(definition)
    for value in definition['enum']:
        validator.validate(value)
    assert not validator.is_valid('unknownMetric')
    assert not validator.is_valid(1)


@pytest.mark.parametrize('metric', ['daysToService', 'distanceToService'])
def test_service_reminders_are_accepted_for_signals_and_synthetics(metric):
    command = SCHEMA['properties']['commands']['items']
    signal = command['properties']['signals']['items']
    synthetic = SCHEMA['properties']['synthetics']['items']
    for definition in [signal, synthetic]:
        Draft7Validator({'definitions': SCHEMA['definitions'], **definition['properties']['suggestedMetric']}).validate(metric)
