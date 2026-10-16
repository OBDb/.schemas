import json
import os

import pytest
from jsonschema import ValidationError, validate

from can.signals import Command

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'signals.json')


@pytest.fixture
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def command_json(**fields):
    return {
        "hdr": "812A",
        "cmd": {"21": "15"},
        "freq": 15,
        "signals": [{"id": "S", "name": "S", "fmt": {"len": 8, "max": 255, "unit": "scalar"}}],
        **fields,
    }


def test_baud_and_init_join_the_command_id():
    command = Command.from_json(command_json(proto="14230", baud=9600, init={"lo": 35, "hi": 15}))
    assert command.id == "812A.2115|b=9600,fi=35-15"
    assert command.iso_baud_rate == 9600
    assert command.fast_init_ms == (35, 15)


def test_a_command_without_them_keeps_its_id():
    assert Command.from_json(command_json(proto="14230")).id == "812A.2115"


def test_commands_differing_only_in_timing_have_different_ids():
    default = Command.from_json(command_json(proto="14230", baud=9600))
    custom = Command.from_json(command_json(proto="14230", baud=9600, init={"lo": 35, "hi": 15}))
    assert default.id != custom.id


def test_schema_accepts_baud_and_init_on_a_14230_command(schema):
    validate({"commands": [command_json(proto="14230", baud=9600, init={"lo": 35, "hi": 15})]}, schema)


def test_schema_accepts_baud_on_a_9141_command(schema):
    validate({"commands": [command_json(proto="9141-2", baud=9600)]}, schema)


@pytest.mark.parametrize("fields", [
    # Neither field means anything without a K-line protocol.
    {"baud": 9600},
    {"init": {"lo": 35, "hi": 15}},
    {"proto": "15765-4-11bit", "baud": 9600},
    # The ISO 9141-2 init is 5-baud, which has no fast-init timing.
    {"proto": "9141-2", "init": {"lo": 35, "hi": 15}},
    # A rate the adapters cannot be set to.
    {"proto": "14230", "baud": 19200},
    # Both times are needed to describe the wake-up pattern.
    {"proto": "14230", "init": {"lo": 35}},
    # Clients pack the timing in 5 ms steps, so anything finer would be lost.
    {"proto": "14230", "init": {"lo": 37.5, "hi": 15}},
    {"proto": "14230", "init": {"lo": 36, "hi": 15}},
    {"proto": "14230", "init": {"lo": 0, "hi": 15}},
    {"proto": "14230", "init": {"lo": 35, "hi": 255}},
])
def test_schema_rejects_timing_outside_a_k_line_command(schema, fields):
    with pytest.raises(ValidationError):
        validate({"commands": [command_json(**fields)]}, schema)
