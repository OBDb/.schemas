import pytest
from typing import Dict, Any, List
import json

from command_registry import CommandRegistry, CommandResponse, ServiceType
from signals import SignalSet, Command, Signal, Scaling, Parameter, ParameterType
from can_frame import CANPacket

def create_test_command(
    pid: int,
    service_type: ServiceType,
    receive_address: str,
    signals: List[Signal]
) -> Command:
    """Helper to create a test command with specified parameters."""
    return Command(
        parameter=Parameter(
            type=ParameterType(service_type.name.replace('SERVICE_', '')),
            value=pid
        ),
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
