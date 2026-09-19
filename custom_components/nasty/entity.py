"""Shared NASty entity support."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from . import NastyConfigEntry
from .const import DOMAIN


def disk_identifier(disk: dict[str, Any]) -> str:
    """Return a stable identifier, including controller transport when needed."""
    if serial := disk.get("serial"):
        return str(serial)
    return f"{disk['device']}:{disk.get('transport') or 'direct'}"


def disk_display_name(disk: dict[str, Any]) -> str:
    """Return a human-readable name that distinguishes identical disk models."""
    device = str(disk["device"]).rsplit("/", 1)[-1]
    if transport := disk.get("transport"):
        device = f"{device}, {transport}"
    return f"{disk.get('model') or 'Disk'} ({device})"


class NastyEntity(CoordinatorEntity[DataUpdateCoordinator[Any]]):
    """Base entity associated with one NASty appliance."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: NastyConfigEntry,
        coordinator: DataUpdateCoordinator[Any],
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the appliance device shared by all entities."""
        info = self._entry.runtime_data.fast.data.info
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=info.get("hostname", self._entry.title),
            manufacturer="NASty",
            model="NASty storage appliance",
            sw_version=info.get("version"),
            configuration_url=self._entry.data["url"],
        )
