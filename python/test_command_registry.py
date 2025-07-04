import pytest
from typing import Any, Dict, List, Optional

from can.command_registry import CommandRegistry, ServiceType
from can.signals import Command, Signal, Scaling, Parameter, ParameterType
from can.can_frame import CANPacket

def create_test_command(
    pid: int,
    service_type: ServiceType,
    receive_address: Optional[str],
    signals: List[Signal]
) -> Command:
    """Helper to create a test command with specified parameters."""
    parameter = Parameter(
        type=ParameterType(service_type.name.replace('SERVICE_', '')),
        value=pid
    )
    id = '7E0.'
    if receive_address:
        id += receive_address + '.'
    id += parameter.as_message()
    return Command(
        id=id,
        parameter=parameter,
        header=0x7E0,
        receive_address=int(receive_address, 16) if receive_address else None,
        signals=tuple(signals),
        update_frequency=1.0
    )

def create_test_signal(
    signal_id: str,
    name: str,
    scaling_params: Dict[str, Any]
) -> Signal:
    """Helper to create a test signal with specified scaling parameters."""
    return Signal(
        id=signal_id,
        name=name,
        description=None,
        format=Scaling(**scaling_params)
    )

def test_ecu_prioritization():
    """Test that commands with specific receive addresses are prioritized over generic commands."""
    # Create two different signals for the same PID but different ECUs
    signal_7ec = create_test_signal(
        "KONAEV_HVBAT_SOC",
        "HV battery charge (7EC)",
        {
            "bit_length": 8,
            "max_value": 255,
            "unit": "scalar"
        }
    )

    signal_7b3 = create_test_signal(
        "KONAEV_IAT_PASS",
        "Passenger temperature (7B3)",
        {
            "bit_length": 8,
            "max_value": 127,
            "divisor": 2,
            "unit": "scalar"
        }
    )

    # Create a command for 7EC ECU (specific)
    command_7ec = create_test_command(
        pid=0x0101,
        service_type=ServiceType.SERVICE_22,
        receive_address="7EC",
        signals=[signal_7ec]
    )

    # Create a generic command (no receive filter)
    command_generic = create_test_command(
        pid=0x0101,
        service_type=ServiceType.SERVICE_22,
        receive_address=None,
        signals=[signal_7b3]
    )

    # Create the registry with both commands
    registry = CommandRegistry([command_7ec, command_generic])

    # Create a response from 7EC ECU
    packet = CANPacket(
        can_identifier="7EC",
        extended_receive_address=None,
        data=bytes.fromhex("6201010A")
    )

    # Process the response
    responses = registry.identify_commands(packet)

    # Verify the correct command was selected
    assert len(responses) == 1
    response = responses[0]

    # Check that we got the 7EC-specific command
    assert response.command == command_7ec

    # Verify the correct signal was decoded
    assert "KONAEV_HVBAT_SOC" in response.values
    assert "KONAEV_IAT_PASS" not in response.values
    assert pytest.approx(response.values["KONAEV_HVBAT_SOC"]) == 10

    # Test with a generic packet
    packet_generic = CANPacket(
        can_identifier="7FF",  # Some other ECU not matching any specific command
        extended_receive_address=None,
        data=bytes.fromhex("6201010A")
    )

    responses_generic = registry.identify_commands(packet_generic)

    # Verify we fall back to the generic command
    assert len(responses_generic) == 1
    response_generic = responses_generic[0]

    # Check that we got the generic command
    assert response_generic.command == command_generic

    # Verify the correct signal was decoded
    assert "KONAEV_IAT_PASS" in response_generic.values
    assert "KONAEV_HVBAT_SOC" not in response_generic.values
    assert pytest.approx(response_generic.values["KONAEV_IAT_PASS"]) == 5.0

def test_identify_service_22_command():
    """Test identifying and decoding a Service 22 command response."""
    # Create test signal for battery voltage
    voltage_signal = create_test_signal(
        "F150_ODO",
        "Odometer (Instrument panel)",
        {
            "bit_length": 24,
            "max_value": 1677721,
            "divisor": 10,
            "unit": "kilometers"
        }
    )

    # Create test command
    command = create_test_command(
        pid=0x404C,
        service_type=ServiceType.SERVICE_22,
        receive_address="728",
        signals=[voltage_signal]
    )

    registry = CommandRegistry([command])

    packet = CANPacket(
        can_identifier="728",
        extended_receive_address=None,
        data=bytes.fromhex("62404C23CE1C")
    )

    responses = registry.identify_commands(packet)

    assert len(responses) == 1
    response = responses[0]
    assert response.command == command
    assert "F150_ODO" in response.values
    assert pytest.approx(response.values["F150_ODO"]) == 234652.4

def test_multiple_signals_in_command():
    """Test decoding multiple signals from a single command response."""
    # Create test signals for tire pressures
    signals = [
        create_test_signal(
            f"TIRE_PRESSURE_{pos}",
            f"Tire Pressure {pos}",
            {
                "bit_offset": i * 8,
                "bit_length": 8,
                "max_value": 255,
                "unit": "psi",
                "divisor": 4
            }
        )
        for i, pos in enumerate(["FL", "FR", "RL", "RR"])
    ]

    command = create_test_command(
        pid=0x2160,
        service_type=ServiceType.SERVICE_22,
        receive_address="7E8",
        signals=signals
    )

    registry = CommandRegistry([command])

    # Response with 4 tire pressures: 32, 33, 31, 32 PSI
    packet = CANPacket(
        can_identifier="7E8",
        extended_receive_address=None,
        data=bytes.fromhex("622160" + "80847C80")
    )

    responses = registry.identify_commands(packet)

    assert len(responses) == 1
    response = responses[0]
    assert response.command == command

    expected_pressures = {
        "TIRE_PRESSURE_FL": 32.0,
        "TIRE_PRESSURE_FR": 33.0,
        "TIRE_PRESSURE_RL": 31.0,
        "TIRE_PRESSURE_RR": 32.0
    }

    for signal_id, expected_value in expected_pressures.items():
        assert signal_id in response.values
        assert pytest.approx(response.values[signal_id]) == expected_value

def test_signed_value_decoding():
    """Test decoding signed values from command responses."""
    signal = create_test_signal(
        "STEERING_ANGLE",
        "Steering Angle",
        {
            "bit_length": 16,
            "max_value": 780.0,
            "min_value": -780.0,
            "unit": "degrees",
            "signed": True,
            "divisor": 10
        }
    )

    command = create_test_command(
        pid=0x3233,
        service_type=ServiceType.SERVICE_22,
        receive_address="7E8",
        signals=[signal]
    )

    registry = CommandRegistry([command])

    # Test positive angle (45.5 degrees)
    packet = CANPacket(
        can_identifier="7E8",
        extended_receive_address=None,
        data=bytes.fromhex("623233" + "01C7")  # 455 after scaling
    )

    responses = registry.identify_commands(packet)
    assert len(responses) == 1
    assert pytest.approx(responses[0].values["STEERING_ANGLE"]) == 45.5

    # Test negative angle (-45.5 degrees)
    packet = CANPacket(
        can_identifier="7E8",
        extended_receive_address=None,
        data=bytes.fromhex("623233" + "FE39")  # -455 after scaling
    )

    responses = registry.identify_commands(packet)
    assert len(responses) == 1
    assert pytest.approx(responses[0].values["STEERING_ANGLE"]) == -45.5

if __name__ == "__main__":
    pytest.main([__file__])
