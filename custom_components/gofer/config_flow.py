import json
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_TOPIC_PREFIX = "gofer/devices/"


class GoferConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo
    ) -> ConfigFlowResult:
        """Handle a flow initialized by an agent announcement over MQTT."""
        topic = discovery_info.topic
        if not topic.startswith(DEVICE_TOPIC_PREFIX):
            return self.async_abort(reason="invalid_discovery_info")
        device_id = topic[len(DEVICE_TOPIC_PREFIX):].strip("/")
        if not device_id or "/" in device_id:
            return self.async_abort(reason="invalid_discovery_info")

        payload: dict = {}
        try:
            parsed = json.loads(discovery_info.payload)
            if isinstance(parsed, dict):
                payload = parsed
        except (ValueError, TypeError):
            _LOGGER.debug("gofer announcement without JSON payload on %s", topic)

        name = str(
            payload.get("name")
            or (payload.get("device") or {}).get("name")
            or device_id
        )
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=name,
            data={
                "device_id": device_id,
                "name": name,
                "capabilities": payload.get("capabilities", {}),
            },
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Manual setup, for devices that have not announced yet."""
        errors: dict = {}
        if user_input is not None:
            device_id = user_input["device_id"].strip()
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get("name") or device_id,
                data={
                    "device_id": device_id,
                    "name": user_input.get("name") or device_id,
                    "capabilities": {},
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("device_id"): str,
                    vol.Optional("name"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """Create the options flow (rename the device)."""
        return GoferOptionsFlow()


class GoferOptionsFlow(OptionsFlow):
    """Options: rename the Gofer device."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Show the rename form."""
        if user_input is not None:
            new_name = user_input["name"].strip() or self.config_entry.title
            device_id = self.config_entry.data["device_id"]
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=new_name,
                data={**self.config_entry.data, "name": new_name},
            )
            device = dr.async_get(self.hass).async_get_device(
                identifiers={(DOMAIN, "gofer_" + device_id)}
            )
            if device is not None:
                dr.async_get(self.hass).async_update_device(
                    device.id, name=new_name
                )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "name",
                        default=self.config_entry.data.get("name")
                        or self.config_entry.title,
                    ): str,
                }
            ),
        )
