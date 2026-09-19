"""NASty integration setup."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NastyApiClient
from .const import CONF_API_TOKEN, CONF_ENABLE_CONTROLS, CONF_URL, CONF_VERIFY_SSL
from .coordinator import NastyFastCoordinator, NastyStorageCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]


@dataclass(slots=True)
class NastyRuntimeData:
    """Runtime objects shared by NASty platforms."""

    client: NastyApiClient
    fast: NastyFastCoordinator
    storage: NastyStorageCoordinator
    controls_enabled: bool


NastyConfigEntry = ConfigEntry[NastyRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: NastyConfigEntry) -> bool:
    """Set up NASty from a config entry."""
    verify_ssl = entry.data[CONF_VERIFY_SSL]
    client = NastyApiClient(
        async_get_clientsession(hass, verify_ssl=verify_ssl),
        entry.data[CONF_URL],
        entry.data[CONF_API_TOKEN],
        verify_ssl=verify_ssl,
    )
    fast = NastyFastCoordinator(hass, entry, client)
    storage = NastyStorageCoordinator(hass, entry, client)
    await fast.async_config_entry_first_refresh()
    await storage.async_config_entry_first_refresh()
    entry.runtime_data = NastyRuntimeData(
        client, fast, storage, entry.data[CONF_ENABLE_CONTROLS]
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NastyConfigEntry) -> bool:
    """Unload a NASty config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: NastyConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
