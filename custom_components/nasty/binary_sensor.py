"""Binary sensors exposed by NASty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NastyConfigEntry
from .coordinator import NastyFastCoordinator, NastyStorageCoordinator
from .entity import NastyEntity, disk_display_name, disk_identifier


class NastySystemHealthBinarySensor(NastyEntity, BinarySensorEntity):
    _attr_name = "System health"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, entry: NastyConfigEntry, coordinator: NastyFastCoordinator) -> None:
        super().__init__(entry, coordinator, "system_health")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.health.get("status") != "ok")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"services": self.coordinator.data.health.get("services", [])}


class NastyUpsConnectedBinarySensor(NastyEntity, BinarySensorEntity):
    _attr_name = "UPS connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, entry: NastyConfigEntry, coordinator: NastyFastCoordinator) -> None:
        super().__init__(entry, coordinator, "ups_connected")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.ups.get("available"))


class NastyRebootRequiredBinarySensor(NastyEntity, BinarySensorEntity):
    _attr_name = "Reboot required"
    _attr_device_class = BinarySensorDeviceClass.UPDATE

    def __init__(self, entry: NastyConfigEntry, coordinator: NastyFastCoordinator) -> None:
        super().__init__(entry, coordinator, "reboot_required")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.reboot_required)


class NastyDiskHealthBinarySensor(NastyEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        entry: NastyConfigEntry,
        coordinator: NastyStorageCoordinator,
        disk: dict[str, Any],
    ) -> None:
        self._disk_id = disk_identifier(disk)
        super().__init__(entry, coordinator, f"disk_{self._disk_id}_health")
        self._attr_name = f"{disk_display_name(disk)} health"

    @property
    def _disk(self) -> dict[str, Any]:
        return next(
            (
                item
                for item in self.coordinator.data.disks
                if disk_identifier(item) == self._disk_id
            ),
            {},
        )

    @property
    def is_on(self) -> bool:
        return not bool(self._disk.get("health_passed", True))

    @property
    def available(self) -> bool:
        return super().available and bool(self._disk)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        disk = self._disk
        return {
            "device": disk.get("device"),
            "model": disk.get("model"),
            "serial": disk.get("serial"),
            "smart_status": disk.get("smart_status"),
            "power_on_hours": disk.get("power_on_hours"),
        }


class NastyFilesystemHealthBinarySensor(NastyEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        entry: NastyConfigEntry,
        coordinator: NastyStorageCoordinator,
        filesystem: dict[str, Any],
    ) -> None:
        self._uuid = filesystem["uuid"]
        super().__init__(entry, coordinator, f"filesystem_{self._uuid}_health")
        self._attr_name = f"{filesystem['name']} health"

    @property
    def _filesystem(self) -> dict[str, Any]:
        return next(
            (fs for fs in self.coordinator.data.filesystems if fs.get("uuid") == self._uuid),
            {},
        )

    @property
    def is_on(self) -> bool:
        filesystem = self._filesystem
        return bool(
            filesystem
            and (not filesystem.get("mounted") or filesystem.get("options", {}).get("degraded"))
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self._filesystem)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        filesystem = self._filesystem
        return {
            "mounted": filesystem.get("mounted"),
            "mount_point": filesystem.get("mount_point"),
            "last_mount_error": filesystem.get("last_mount_error"),
        }


async def async_setup_entry(
    hass: Any, entry: NastyConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    async_add_entities(
        [
            NastySystemHealthBinarySensor(entry, runtime.fast),
            NastyUpsConnectedBinarySensor(entry, runtime.fast),
            NastyRebootRequiredBinarySensor(entry, runtime.fast),
        ]
    )

    known_disks: set[str] = set()
    known_filesystems: set[str] = set()

    @callback
    def add_disk_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for filesystem in runtime.storage.data.filesystems:
            uuid = filesystem.get("uuid")
            if uuid and uuid not in known_filesystems:
                known_filesystems.add(uuid)
                entities.append(
                    NastyFilesystemHealthBinarySensor(entry, runtime.storage, filesystem)
                )
        for disk in runtime.storage.data.disks:
            disk_id = disk_identifier(disk)
            if disk_id and disk_id not in known_disks:
                known_disks.add(disk_id)
                entities.append(NastyDiskHealthBinarySensor(entry, runtime.storage, disk))
        if entities:
            async_add_entities(entities)

    add_disk_entities()
    entry.async_on_unload(runtime.storage.async_add_listener(add_disk_entities))
