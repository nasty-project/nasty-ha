"""Tests for appliance sensor presentation."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricPotential
from nasty.coordinator import NastyFastData
from nasty.sensor import SYSTEM_SENSORS


def test_ups_voltage_sensors_map_api_values() -> None:
    data = NastyFastData({}, {}, {}, [], {}, [], [], {
        "input_voltage": 239.2,
        "output_voltage": 238.7,
    }, False)
    descriptions = {description.key: description for description in SYSTEM_SENSORS}

    for key, expected in (
        ("ups_input_voltage", 239.2),
        ("ups_output_voltage", 238.7),
    ):
        description = descriptions[key]
        assert description.value(data) == expected
        assert description.native_unit == UnitOfElectricPotential.VOLT
        assert description.device_class == SensorDeviceClass.VOLTAGE
        assert description.state_class == SensorStateClass.MEASUREMENT
