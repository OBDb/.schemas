import pytest

from can.signals import Command


def command(**fields) -> Command:
    return Command.from_json({
        "cmd": {"22": "DA2C"},
        "freq": 1,
        "signals": [{"id": "S", "name": "S", "fmt": {"len": 8, "max": 255, "unit": "scalar"}}],
        **fields,
    })


@pytest.mark.parametrize("fields, reply_id", [
    # One byte: the ISO pp DA F1 xx reply at the command's priority.
    ({"hdr": "DA10", "rax": "10"}, 0x18DAF110),
    ({"hdr": "DA10", "rax": "10", "pri": "14"}, 0x14DAF110),
    # Six digits: the command's priority over the low 24 bits.
    ({"hdr": "FC00", "rax": "FE007B", "pri": "17"}, 0x17FE007B),
    # Eight digits: the reply's whole ID, whatever the request's priority.
    ({"hdr": "D016", "rax": "1EC60E80", "pri": "1D", "tst": "30"}, 0x1EC60E80),
    ({"hdr": "D016", "rax": "1EC60E80"}, 0x1EC60E80),
    # 11-bit: the rax as written.
    ({"hdr": "7E0", "rax": "7E8"}, 0x7E8),
])
def test_receive_address_is_the_reply_id_the_command_answers_on(fields, reply_id):
    assert command(**fields).receive_address == reply_id
