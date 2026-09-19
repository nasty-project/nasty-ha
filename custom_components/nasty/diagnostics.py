"""Diagnostics support for NASty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import NastyConfigEntry
from .const import CONF_API_TOKEN

TO_REDACT = {CONF_API_TOKEN, "addresses", "engine_commit", "raw", "serial"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: NastyConfigEntry
) -> dict[str, Any]:
    """Return non-sensitive configuration and the latest coordinator data."""
    runtime = entry.runtime_data
    diagnostics = {
        "config_entry": entry.data,
        "fast": {
            "info": runtime.fast.data.info,
            "stats": runtime.fast.data.stats,
            "health": runtime.fast.data.health,
            "alerts": runtime.fast.data.alerts,
            "apps_status": runtime.fast.data.apps_status,
            "apps": runtime.fast.data.apps,
            "vms": runtime.fast.data.vms,
            "ups": runtime.fast.data.ups,
            "reboot_required": runtime.fast.data.reboot_required,
        },
        "storage": {
            "filesystems": runtime.storage.data.filesystems,
            "disks": runtime.storage.data.disks,
        },
    }
    return async_redact_data(diagnostics, TO_REDACT)
