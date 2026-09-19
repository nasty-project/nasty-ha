"""Optional VM and App controls for NASty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NastyConfigEntry
from .api import NastyApiError
from .coordinator import NastyFastCoordinator
from .entity import NastyEntity


class NastyVmSwitch(NastyEntity, SwitchEntity):
    _attr_icon = "mdi:desktop-tower"

    def __init__(
        self, entry: NastyConfigEntry, coordinator: NastyFastCoordinator, vm: dict[str, Any]
    ) -> None:
        self._vm_id = vm["id"]
        super().__init__(entry, coordinator, f"vm_{self._vm_id}")
        self._attr_name = f"VM {vm['name']}"

    @property
    def _vm(self) -> dict[str, Any] | None:
        return next((vm for vm in self.coordinator.data.vms if vm.get("id") == self._vm_id), None)

    @property
    def available(self) -> bool:
        return super().available and self._vm is not None

    @property
    def is_on(self) -> bool:
        return bool(self._vm and self._vm.get("running"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._call("vm.start")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._call("vm.stop")

    async def _call(self, method: str) -> None:
        try:
            await self._entry.runtime_data.client.post(method, id=self._vm_id)
        except NastyApiError as error:
            raise HomeAssistantError(str(error)) from error
        await self.coordinator.async_request_refresh()


class NastyAppSwitch(NastyEntity, SwitchEntity):
    _attr_icon = "mdi:docker"

    def __init__(
        self, entry: NastyConfigEntry, coordinator: NastyFastCoordinator, app: dict[str, Any]
    ) -> None:
        self._app_name = app["name"]
        super().__init__(entry, coordinator, f"app_{self._app_name}")
        self._attr_name = f"App {self._app_name}"

    @property
    def _app(self) -> dict[str, Any] | None:
        return next(
            (app for app in self.coordinator.data.apps if app.get("name") == self._app_name), None
        )

    @property
    def available(self) -> bool:
        return super().available and self._app is not None

    @property
    def is_on(self) -> bool:
        return bool(self._app and self._app.get("status") == "running")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._call("apps.start")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._call("apps.stop")

    async def _call(self, method: str) -> None:
        try:
            await self._entry.runtime_data.client.post(method, name=self._app_name)
        except NastyApiError as error:
            raise HomeAssistantError(str(error)) from error
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: Any, entry: NastyConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    if not runtime.controls_enabled:
        return

    known_vms: set[str] = set()
    known_apps: set[str] = set()

    @callback
    def add_control_entities() -> None:
        entities: list[SwitchEntity] = []
        for vm in runtime.fast.data.vms:
            vm_id = vm.get("id")
            if vm_id and vm_id not in known_vms:
                known_vms.add(vm_id)
                entities.append(NastyVmSwitch(entry, runtime.fast, vm))
        for app in runtime.fast.data.apps:
            name = app.get("name")
            if name and name not in known_apps:
                known_apps.add(name)
                entities.append(NastyAppSwitch(entry, runtime.fast, app))
        if entities:
            async_add_entities(entities)

    add_control_entities()
    entry.async_on_unload(runtime.fast.async_add_listener(add_control_entities))
