"""Finds a VIN in a captured response, so that one never reaches a published test case.

A response line is a CAN header followed by an ISO-TP frame. Frames are reassembled per header
before searching, because a VIN spans three frames. A 17-character run counts as a VIN when it
follows a VIN reply (49 02, 62 F190 or 5A 90), or when its check digit is valid; the check digit
keeps random ASCII-looking bytes from counting.
"""

import re
from collections import defaultdict
from typing import Iterable

_VIN = re.compile(rb'[A-HJ-NPR-Z0-9]{17,}')
_VIN_REPLY = re.compile(rb'(?:\x49\x02\x01?|\x62\xf1\x90|\x5a\x90)[\x00-\x20]*([A-HJ-NPR-Z0-9]{17})')
_TRANSLITERATION = {
    **{str(i): i for i in range(10)},
    **dict(zip('ABCDEFGH', range(1, 9))),
    **dict(zip('JKLMN', range(1, 6))),
    'P': 7, 'R': 9,
    **dict(zip('STUVWXYZ', range(2, 10))),
}
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def _check_digit_valid(vin: str) -> bool:
    remainder = sum(_TRANSLITERATION[c] * w for c, w in zip(vin, _WEIGHTS)) % 11
    return vin[8] == ('X' if remainder == 10 else str(remainder))


def _plausible(vin: str) -> bool:
    # A model year code is never 0, U or Z, and a run of one repeated byte is padding.
    return vin[9] not in '0UZ' and len(set(vin)) >= 7 and _check_digit_valid(vin)


def _header_length(line: str):
    # Data is whole bytes, so an odd-length line has a three-digit 11-bit ID and an even one a
    # two-byte 11-bit ID (07E8) or a 29-bit ID (18DAF110).
    if len(line) <= 4 or not re.fullmatch(r'[0-9A-Fa-f]+', line):
        return None
    if len(line) % 2:
        return 3
    return 8 if line[:2] == '18' and len(line) > 10 else 4


def _payloads(response: str) -> Iterable[bytes]:
    # Each line is read both without and with an extended address byte before the PCI, since a
    # capture can mix modules of each kind.
    by_module = defaultdict(bytearray)
    for line in response.splitlines():
        line = ''.join(line.split())
        header = _header_length(line)
        if header is None:
            continue
        data = bytes.fromhex(line[header:])
        for address_bytes in (0, 1):
            if len(data) <= address_bytes:
                continue
            pci = data[address_bytes]
            module = (line[:header], address_bytes, data[:address_bytes])
            by_module[module] += data[address_bytes + (2 if pci >> 4 == 1 else 1):]
    return [bytes(p) for p in by_module.values()]


def contains_vin(response: str) -> bool:
    """Whether any module's reply in a captured response holds a VIN."""
    for payload in _payloads(response):
        if _VIN_REPLY.search(payload):
            return True
        # Only a run's first 17 characters: about one window in eleven passes the check digit,
        # so trying every window of a long run of text would find one sooner or later.
        if any(_plausible(m[:17].decode()) for m in _VIN.findall(payload)):
            return True
    return False
