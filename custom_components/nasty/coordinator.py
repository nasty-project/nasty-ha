"""Data update coordinators for NASty."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NastyApiClient, NastyApiError, NastyAuthenticationError
from .const import DOMAIN, FAST_UPDATE_INTERVAL, STORAGE_UPDATE_INTERVAL

JsonObject = dict[str, Any]
LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class NastyFastData:
    """Frequently refreshed appliance state."""

    info: JsonObject
    stats: JsonObject
    health: JsonObject
    alerts: list[JsonObject]
    apps_status: JsonObject
    apps: list[JsonObject]
    vms: list[JsonObject]
    ups: JsonObject
    reboot_required: bool


@dataclass(slots=True)
class NastyStorageData:
    """Slower storage and SMART state."""

    filesystems: list[JsonObject]
    disks: list[JsonObject]


class NastyFastCoordinator(DataUpdateCoordinator[NastyFastData]):
    """Refresh system and runtime state."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: NastyApiClient
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}-fast",
            update_interval=FAST_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> NastyFastData:
        try:
            info, stats, health, alerts, apps_status, apps, vms, ups, reboot_required = (
                await asyncio.gather(
                    self.client.get("system.info"),
                    self.client.get("system.stats"),
                    self.client.get("system.health"),
                    self.client.get_optional("system.alerts", []),
                    self.client.get_optional("apps.status", {}),
                    self.client.get_optional("apps.list", []),
                    self.client.get_optional("vm.list", []),
                    self.client.get_optional("system.nut.status", {}),
                    self.client.get_optional("system.reboot_required", False),
                )
            )
        except NastyAuthenticationError as error:
            raise ConfigEntryAuthFailed from error
        except NastyApiError as error:
            raise UpdateFailed(str(error)) from error
        return NastyFastData(
            info, stats, health, alerts, apps_status, apps, vms, ups, reboot_required
        )


class NastyStorageCoordinator(DataUpdateCoordinator[NastyStorageData]):
    """Refresh filesystems and disk health without polling SMART too often."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: NastyApiClient
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}-storage",
            update_interval=STORAGE_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> NastyStorageData:
        try:
            filesystems, disks = await asyncio.gather(
                self.client.get("fs.list"),
                self.client.get_optional("system.disks", []),
            )
        except NastyAuthenticationError as error:
            raise ConfigEntryAuthFailed from error
        except NastyApiError as error:
            raise UpdateFailed(str(error)) from error
        return NastyStorageData(filesystems, disks)
