"""The Gofer integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.mqtt import ReceiveMessage, async_subscribe
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN, INFO_TOPIC, PLATFORMS
from .notify import async_register_notify_service

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Gofer integration."""
    hass.data.setdefault(DOMAIN, {})
    async_register_notify_service(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Gofer device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    device_id: str = entry.data["device_id"]
    capabilities: dict = dict(entry.data.get("capabilities") or {})

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "gofer_" + device_id)},
        manufacturer="Gofer",
        model="Gofer Agent",
        name=entry.title,
        sw_version=str(capabilities.get("sw_version") or ""),
    )

    unsubs: list = []

    @callback
    def _on_info(msg: ReceiveMessage) -> None:
        nonlocal capabilities
        try:
            payload = json.loads(msg.payload)
        except (ValueError, TypeError):
            return
        if not isinstance(payload, dict):
            return
        new_caps = payload.get("capabilities")
        if isinstance(new_caps, dict) and new_caps != capabilities:
            _LOGGER.debug("gofer capabilities changed for %s", device_id)
            need_reload = any(
                bool(new_caps.get(key)) != bool(capabilities.get(key))
                for key in ("media_player", "notifications")
            )
            capabilities = dict(new_caps)
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, "capabilities": capabilities},
            )
            sw = (payload.get("device") or {}).get("sw_version")
            if sw:
                dev = device_registry.async_get_device(
                    identifiers={(DOMAIN, "gofer_" + device_id)}
                )
                if dev is not None and dev.sw_version != str(sw):
                    device_registry.async_update_device(
                        dev.id, sw_version=str(sw)
                    )
            if need_reload:
                hass.async_create_task(
                    hass.config_entries.async_reload(entry.entry_id)
                )

    info_topic = INFO_TOPIC.format(device_id=device_id)
    unsubs.append(await async_subscribe(hass, info_topic, _on_info))

    hass.data[DOMAIN][entry.entry_id] = {
        "device_id": device_id,
        "capabilities": capabilities,
        "unsubs": unsubs,
    }

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Gofer config entry."""
    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if data:
        for unsub in data.get("unsubs", []):
            unsub()
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if not unload_ok:
            return False
    return True
