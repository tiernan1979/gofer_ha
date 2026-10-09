"""Media player platform for Gofer agents."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.components.mqtt import ReceiveMessage, async_publish, async_subscribe
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    AVAILABILITY_TOPIC,
    DOMAIN,
    MEDIA_COMMAND_TOPIC,
    MEDIA_STATE_TOPIC,
    MEDIA_VOLUME_SET_TOPIC,
    MEDIA_VOLUME_TOPIC,
)

_LOGGER = logging.getLogger(__name__)

_STATE_MAP = {
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
    "idle": MediaPlayerState.IDLE,
    "off": MediaPlayerState.OFF,
    "on": MediaPlayerState.IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Gofer media player from a config entry."""
    capabilities = entry.data.get("capabilities") or {}
    if not capabilities.get("media_player", True):
        return
    async_add_entities([GoferMediaPlayer(hass, entry)])


class GoferMediaPlayer(MediaPlayerEntity):
    """Media controls for a Gofer agent."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Media"
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
    )
    _attr_volume_step = 0.1

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the media player."""
        self.hass = hass
        self._entry = entry
        self._device_id: str = entry.data["device_id"]
        self._attr_unique_id = f"gofer_{self._device_id}_media_player"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"gofer_{self._device_id}")},
        }
        self._state = MediaPlayerState.IDLE
        self._volume: float | None = None
        self._available = True
        self._unsubs: list[Any] = []

    @property
    def available(self) -> bool:
        """Return whether the agent is reachable."""
        return self._available

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the current state."""
        if not self._available:
            return None
        return self._state

    @property
    def volume_level(self) -> float | None:
        """Return the volume level 0..1."""
        return self._volume

    async def async_added_to_hass(self) -> None:
        """Subscribe to agent topics."""
        await super().async_added_to_hass()
        did = self._device_id

        @callback
        def _state(msg: ReceiveMessage) -> None:
            new = _STATE_MAP.get(msg.payload.strip().lower())
            if new is None:
                _LOGGER.debug("unknown media state %r", msg.payload)
                return
            if new != self._state:
                self._state = new
                self.async_write_ha_state()

        @callback
        def _volume(msg: ReceiveMessage) -> None:
            try:
                value = float(msg.payload)
            except ValueError:
                return
            value = min(max(value, 0.0), 1.0)
            if value != self._volume:
                self._volume = value
                self.async_write_ha_state()

        @callback
        def _availability(msg: ReceiveMessage) -> None:
            available = msg.payload.strip().lower() == "online"
            if available != self._available:
                self._available = available
                self.async_write_ha_state()

        self._unsubs.append(
            await async_subscribe(
                self.hass, MEDIA_STATE_TOPIC.format(device_id=did), _state
            )
        )
        self._unsubs.append(
            await async_subscribe(
                self.hass, MEDIA_VOLUME_TOPIC.format(device_id=did), _volume
            )
        )
        self._unsubs.append(
            await async_subscribe(
                self.hass,
                AVAILABILITY_TOPIC.format(device_id=did),
                _availability,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from agent topics."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs = []

    async def _publish_command(self, payload: str) -> None:
        topic = MEDIA_COMMAND_TOPIC.format(device_id=self._device_id)
        await async_publish(self.hass, topic, payload)

    async def async_media_play(self) -> None:
        """Send play to the agent."""
        await self._publish_command("play")

    async def async_media_pause(self) -> None:
        """Send pause to the agent."""
        await self._publish_command("pause")

    async def async_media_stop(self) -> None:
        """Send stop to the agent."""
        await self._publish_command("stop")

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume on the agent."""
        topic = MEDIA_VOLUME_SET_TOPIC.format(device_id=self._device_id)
        await async_publish(self.hass, topic, f"{volume:.2f}")
        self._volume = min(max(volume, 0.0), 1.0)
        self.async_write_ha_state()

    async def async_increment_volume(self) -> None:
        """Raise the volume by one step."""
        base = self._volume if self._volume is not None else 0.0
        await self.async_set_volume_level(min(base + self.volume_step, 1.0))

    async def async_decrement_volume(self) -> None:
        """Lower the volume by one step."""
        base = self._volume if self._volume is not None else 1.0
        await self.async_set_volume_level(max(base - self.volume_step, 0.0))
