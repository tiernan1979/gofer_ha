"""Diagnostics support for Gofer."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a Gofer config entry."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, "gofer_" + entry.data["device_id"])}
    )

    device_info: dict[str, Any] | None = None
    if device is not None:
        device_info = {
            "name": device.name_by_user or device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "entities": sorted(
                e.entity_id
                for e in er.async_entries_for_device(er.async_get(hass), device.id)
            ),
        }

    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "domain": entry.domain,
                "device_id": entry.data.get("device_id"),
                "name": entry.data.get("name"),
                "capabilities": entry.data.get("capabilities"),
                "version": entry.version,
            },
            [],
        ),
        "device": device_info,
        "hass_state": hass.state,
    }
