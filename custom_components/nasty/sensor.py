"""Sensors exposed by NASty."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTemperature, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NastyConfigEntry
from .coordinator import NastyFastCoordinator, NastyFastData, NastyStorageCoordinator
from .entity import NastyEntity, disk_identifier


@dataclass(frozen=True, kw_only=True)
class NastySensorDescription:
    key: str
    name: str
    value: Callable[[NastyFastData], Any]
    native_unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None


def _memory_percent(data: NastyFastData) -> float | None:
    memory = data.stats.get("memory", {})
    total = memory.get("total_bytes", 0)
    return round(memory.get("used_bytes", 0) * 100 / total, 1) if total else None


SYSTEM_SENSORS = (
    NastySensorDescription(
        key="cpu_temperature",
        name="CPU temperature",
        value=lambda data: data.stats.get("cpu", {}).get("temp_c"),
        native_unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NastySensorDescription(
        key="load_1",
        name="Load average (1 minute)",
        value=lambda data: data.stats.get("cpu", {}).get("load_1"),
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    NastySensorDescription(
        key="memory_usage",
        name="Memory usage",
        value=_memory_percent,
        native_unit=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:memory",
    ),
    NastySensorDescription(
        key="uptime",
        name="Uptime",
        value=lambda data: data.info.get("uptime_seconds"),
        native_unit=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    NastySensorDescription(
        key="active_alerts",
        name="Active alerts",
        value=lambda data: len(data.alerts),
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle-outline",
    ),
    NastySensorDescription(
        key="apps_count",
        name="Apps",
        value=lambda data: data.apps_status.get("app_count"),
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:apps",
    ),
    NastySensorDescription(
        key="apps_memory",
        name="Apps memory",
        value=lambda data: data.apps_status.get("memory_bytes"),
        native_unit=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NastySensorDescription(
        key="ups_battery",
        name="UPS battery",
        value=lambda data: data.ups.get("battery_charge"),
        native_unit=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NastySensorDescription(
        key="ups_runtime",
        name="UPS runtime",
        value=lambda data: data.ups.get("battery_runtime"),
        native_unit=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NastySensorDescription(
        key="ups_load",
        name="UPS load",
        value=lambda data: data.ups.get("ups_load"),
        native_unit=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
    ),
)


class NastySystemSensor(NastyEntity, SensorEntity):
    def __init__(
        self,
        entry: NastyConfigEntry,
        coordinator: NastyFastCoordinator,
        description: NastySensorDescription,
    ) -> None:
        super().__init__(entry, coordinator, description.key)
        self._description = description
        self._attr_name = description.name
        self._attr_native_unit_of_measurement = description.native_unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_icon = description.icon

    @property
    def native_value(self) -> Any:
        return self._description.value(self.coordinator.data)


class NastyFilesystemUsageSensor(NastyEntity, SensorEntity):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:database"

    def __init__(
        self,
        entry: NastyConfigEntry,
        coordinator: NastyStorageCoordinator,
        filesystem: dict[str, Any],
    ) -> None:
        self._uuid = filesystem["uuid"]
        super().__init__(entry, coordinator, f"filesystem_{self._uuid}_usage")
        self._attr_name = f"{filesystem['name']} usage"

    @property
    def native_value(self) -> float | None:
        filesystem = next(
            (fs for fs in self.coordinator.data.filesystems if fs.get("uuid") == self._uuid), None
        )
        if not filesystem or not filesystem.get("total_bytes"):
            return None
        return float(round(filesystem["used_bytes"] * 100 / filesystem["total_bytes"], 1))

    @property
    def available(self) -> bool:
        return super().available and any(
            fs.get("uuid") == self._uuid for fs in self.coordinator.data.filesystems
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        filesystem: dict[str, Any] = next(
            (fs for fs in self.coordinator.data.filesystems if fs.get("uuid") == self._uuid), {}
        )
        return {
            "mounted": filesystem.get("mounted"),
            "used_bytes": filesystem.get("used_bytes"),
            "available_bytes": filesystem.get("available_bytes"),
            "total_bytes": filesystem.get("total_bytes"),
        }


class NastyDiskTemperatureSensor(NastyEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        entry: NastyConfigEntry,
        coordinator: NastyStorageCoordinator,
        disk: dict[str, Any],
    ) -> None:
        self._disk_id = disk_identifier(disk)
        super().__init__(entry, coordinator, f"disk_{self._disk_id}_temperature")
        self._attr_name = f"{disk.get('model') or disk['device']} temperature"

    @property
    def native_value(self) -> int | None:
        disk = next(
            (
                item
                for item in self.coordinator.data.disks
                if disk_identifier(item) == self._disk_id
            ),
            None,
        )
        return disk.get("temperature_c") if disk else None

    @property
    def available(self) -> bool:
        return super().available and any(
            disk_identifier(item) == self._disk_id for item in self.coordinator.data.disks
        )


async def async_setup_entry(
    hass: Any, entry: NastyConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    async_add_entities(
        NastySystemSensor(entry, runtime.fast, description) for description in SYSTEM_SENSORS
    )

    known_filesystems: set[str] = set()
    known_disks: set[str] = set()

    @callback
    def add_storage_entities() -> None:
        entities: list[SensorEntity] = []
        for filesystem in runtime.storage.data.filesystems:
            uuid = filesystem.get("uuid")
            if uuid and uuid not in known_filesystems:
                known_filesystems.add(uuid)
                entities.append(NastyFilesystemUsageSensor(entry, runtime.storage, filesystem))
        for disk in runtime.storage.data.disks:
            disk_id = disk_identifier(disk)
            if disk_id and disk_id not in known_disks and disk.get("temperature_c") is not None:
                known_disks.add(disk_id)
                entities.append(NastyDiskTemperatureSensor(entry, runtime.storage, disk))
        if entities:
            async_add_entities(entities)

    add_storage_entities()
    entry.async_on_unload(runtime.storage.async_add_listener(add_storage_entities))
