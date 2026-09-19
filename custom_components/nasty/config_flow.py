"""Config flow for NASty."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    NastyApiClient,
    NastyApiError,
    NastyAuthenticationError,
    NastyCannotConnectError,
    normalize_url,
)
from .const import (
    CONF_API_TOKEN,
    CONF_ENABLE_CONTROLS,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_ENABLE_CONTROLS,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    url = normalize_url(data[CONF_URL])
    verify_ssl = data[CONF_VERIFY_SSL]
    client = NastyApiClient(
        async_get_clientsession(hass, verify_ssl=verify_ssl),
        url,
        data[CONF_API_TOKEN],
        verify_ssl=verify_ssl,
    )
    info = await client.validate()
    return {"url": url, "hostname": info["hostname"]}


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_URL, default=values.get(CONF_URL, "https://nasty.local")
            ): vol.All(str, vol.Length(min=1)),
            vol.Required(
                CONF_API_TOKEN, default=values.get(CONF_API_TOKEN, "")
            ): vol.All(str, vol.Length(min=1)),
            vol.Required(
                CONF_VERIFY_SSL,
                default=values.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): bool,
            vol.Required(
                CONF_ENABLE_CONTROLS,
                default=values.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS),
            ): bool,
        }
    )


class NastyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a NASty config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure a NASty appliance."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validated = await _validate_input(self.hass, user_input)
            except NastyAuthenticationError:
                errors["base"] = "invalid_auth"
            except (NastyCannotConnectError, TimeoutError):
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_url"
            except NastyApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(validated["url"])
                self._abort_if_unique_id_configured()
                data = {**user_input, CONF_URL: validated["url"]}
                return self.async_create_entry(title=validated["hostname"], data=data)

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Start token reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Update an expired or revoked API token."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            updated = {**entry.data, CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
            try:
                await _validate_input(self.hass, updated)
            except NastyAuthenticationError:
                errors["base"] = "invalid_auth"
            except (NastyCannotConnectError, TimeoutError):
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_url"
            except NastyApiError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(entry, data=updated)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_API_TOKEN): vol.All(str, vol.Length(min=1))}
            ),
            errors=errors,
        )
