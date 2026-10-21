"""Tests for finding a VIN in a captured response."""

import os
import tempfile

import pytest

from signals_testing import obd_yaml_testrunner
from vin import contains_vin

# A published sample VIN with a valid check digit, not a real car's.
SAMPLE = '1M8GDM9AXKP042788'


def frames(header: str, payload: bytes) -> str:
    """ISO-TP frames for a payload, one response line each."""
    if len(payload) <= 7:
        return f'{header}{len(payload):02X}{payload.hex().upper()}'
    lines = [f'{header}1{len(payload) >> 8:01X}{len(payload) & 0xFF:02X}{payload[:6].hex().upper()}']
    rest, seq = payload[6:], 1
    while rest:
        lines.append(f'{header}2{seq & 0xF:X}{rest[:7].hex().upper().ljust(14, "5")}')
        rest, seq = rest[7:], seq + 1
    return '\n'.join(lines)


@pytest.mark.parametrize('prefix', [b'\x62\xf1\x90', b'\x49\x02\x01', b'\x5a\x90'])
def test_vin_replies_found(prefix):
    assert contains_vin(frames('18DAF110', prefix + SAMPLE.encode()))
    assert contains_vin(frames('7E8', prefix + SAMPLE.encode()))


def test_vin_reply_without_a_check_digit_found():
    # European VINs need not carry a check digit; the reply prefix is enough.
    assert contains_vin(frames('7E8', b'\x49\x02\x01' + b'WVWZZZ1KZAW000001'))


def test_vin_mixed_into_another_reply_found():
    response = frames('7E8', b'\x41\x05\x4e') + '\n' + frames('7E8', b'\x00\x00' + SAMPLE.encode())
    assert contains_vin(response)


def test_vin_split_across_interleaved_modules_found():
    vin = frames('18DAF110', b'\x62\xf1\x90' + SAMPLE.encode()).split('\n')
    other = frames('18DAF128', b'\x62\x40\x33' + bytes(range(20))).split('\n')
    assert contains_vin('\n'.join(x for pair in zip(vin, other) for x in pair))


@pytest.mark.parametrize('response', [
    '7E8064105' + '4E' * 4,
    frames('18DAF110', b'\x62\x20\x28' + b'J4JJ4JJ4JJ4JJ4JJ4J' * 2),
    frames('18DAF110', b'\x62\xf1\x81' + b'37805-5PA-A530'),
    frames('7E8', b'\x62\x10\x00' + b'1' * 17),
])
def test_other_replies_not_found(response):
    assert not contains_vin(response)


def test_fixture_with_vin_fails():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, '2020', 'commands', '7E0.0105.yaml')
        os.makedirs(os.path.dirname(path))
        response = frames('7E8', b'\x49\x02\x01' + SAMPLE.encode()).replace('\n', '\n    ')
        with open(path, 'w') as f:
            f.write(f'command_id: 7E0.0105\ntest_cases:\n- expected_values: {{}}\n  response: |-\n    {response}\n')
        with pytest.raises(AssertionError, match='test case 0 has a VIN') as e:
            obd_yaml_testrunner(path)
        assert SAMPLE not in str(e.value)
