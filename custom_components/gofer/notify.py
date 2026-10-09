"""Notification service and entity for Gofer agents."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_NOTIFICATION, SERVICE_NOTIFY

_LOGGER = logging.getLogger(__name__)

NOTIFY_SCHEMA = vol.Schema(
    {
        vol.Required("message"): vol.All(cv.string),
        vol.Optional("title"): vol.All(cv.string),
        vol.Optional("device_id"): vol.All(cv.ensure_list, [str]),
        vol.Optional("actions"): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("action_id"): vol.All(cv.string),
                        vol.Required("title"): vol.All(cv.string),
                        vol.Optional("uri"): vol.All(cv.string),
                    }
                )
            ]
        ),
    }
)


def _fire_notification(
    hass: HomeAssistant,
    device_id: str,
    title: str,
    message: str,
    actions: list[dict[str, Any]] | None = None,
) -> None:
    hass.bus.async_fire(
        EVENT_NOTIFICATION,
        {
            "device_id": device_id,
            "notification_id": "gofer-" + uuid.uuid4().hex,
            "title": title,
            "message": message,
            "actions": actions or [],
        },
    )


@callback
def async_register_notify_service(hass: HomeAssistant) -> None:
    """Register the gofer.notify service once per HA instance."""
    if hass.services.has_service(DOMAIN, SERVICE_NOTIFY):
        return

    async def _handle_notify(call: ServiceCall) -> None:
        device_registry = dr.async_get(hass)
        entries = list(hass.config_entries.async_entries(DOMAIN))

        targets: list[str] = []
        requested = call.data.get("device_id") or []
        if requested:
            for dev_id in requested:
                device = device_registry.async_get(dev_id)
                if device is None:
                    _LOGGER.warning("gofer.notify: unknown device %s", dev_id)
                    continue
                for domain, identifier in device.identifiers:
                    if domain == DOMAIN and identifier.startswith("gofer_"):
                        targets.append(identifier[len("gofer_"):])
        else:
            targets = [e.data["device_id"] for e in entries]

        if not targets:
            _LOGGER.warning("gofer.notify: no configured Gofer devices")
            return

        actions = [
            {
                "action_id": a["action_id"],
                "title": a["title"],
                **({"uri": a["uri"]} if a.get("uri") else {}),
            }
            for a in (call.data.get("actions") or [])
        ]

        for device_id in targets:
            _fire_notification(
                hass,
                device_id,
                call.data.get("title") or "Gofer",
                call.data["message"],
                actions,
            )

    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY, _handle_notify, schema=NOTIFY_SCHEMA
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Gofer notify entity from a config entry."""
    capabilities = entry.data.get("capabilities") or {}
    if not capabilities.get("notifications", True):
        return
    async_add_entities([GoferNotifyEntity(hass, entry)])


class GoferNotifyEntity(NotifyEntity):
    """Send notifications to a single Gofer agent."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Notification"
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the notify entity."""
        self.hass = hass
        self._entry = entry
        self._device_id: str = entry.data["device_id"]
        self._attr_unique_id = f"gofer_{self._device_id}_notify"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"gofer_{self._device_id}")},
        }

    async def async_send_message(
        self, message: str, title: str | None = None, **kwargs: Any
    ) -> None:
        """Send a notification to the agent."""
        _fire_notification(
            self.hass,
            self._device_id,
            title or "Gofer",
            message,
        )


def describe_service() -> dict[str, Any]:
    """Return service metadata (used by translations)."""
    return {"service": SERVICE_NOTIFY, "name": "Send notification"}
