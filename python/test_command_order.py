import json
import os
import subprocess
import sys
from pathlib import Path

from can.signals import SignalSet

# Make repos collect each model's version of a command, so one parameter often
# has several definitions. Which one decodes a reply must not depend on the
# hash seed.
SIGNALSET = json.dumps({"commands": [
    {"hdr": "7E0", "cmd": {"22": "1E12"}, "freq": 1, "signals": [
        {"id": "GEAR", "name": "Gear", "fmt": {"len": 8, "max": 255, "unit": "scalar"}}]},
    {"hdr": "7E2", "cmd": {"22": "1E12"}, "freq": 1, "signals": [
        {"id": "GEAR", "name": "Gear", "fmt": {"len": 8, "max": 255, "div": 2, "unit": "scalar"}}]},
    {"hdr": "7E4", "cmd": {"22": "1E12"}, "freq": 1, "signals": [
        {"id": "GEAR", "name": "Gear", "fmt": {"len": 8, "max": 255, "div": 4, "unit": "scalar"}}]},
]})

DECODE = """
import sys
from can.can_frame import CANFrameScanner
from can.command_registry import CommandRegistry
from can.signals import SignalSet
registry = CommandRegistry(list(SignalSet.from_json(sys.argv[1]).commands))
values = {}
for packet in CANFrameScanner.from_ascii_string("7E804621E1208"):
    for response in registry.identify_commands(packet):
        values.update(response.values)
print(values)
"""


def test_commands_keep_the_file_order():
    headers = [command.id.split(".")[0] for command in SignalSet.from_json(SIGNALSET).commands]
    assert headers == ["7E0", "7E2", "7E4"]


def test_decode_is_the_same_for_every_hash_seed():
    python_dir = Path(__file__).parent
    outputs = set()
    for seed in range(8):
        result = subprocess.run(
            [sys.executable, "-c", DECODE, SIGNALSET],
            cwd=python_dir, capture_output=True, text=True, check=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
        )
        outputs.add(result.stdout)
    assert len(outputs) == 1, outputs
