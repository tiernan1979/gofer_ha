DOMAIN = "gofer"

PLATFORMS: list[str] = ["media_player", "notify"]

EVENT_NOTIFICATION = "gofer_notification"
EVENT_NOTIFICATION_ACTION = "gofer_notification_action"
EVENT_MEDIA_PLAYER_COMMAND = "gofer_media_player_command"

SERVICE_NOTIFY = "notify"

INFO_TOPIC = "gofer/{device_id}/info"
AVAILABILITY_TOPIC = "gofer/{device_id}/availability"
MEDIA_STATE_TOPIC = "gofer/{device_id}/media_player/state"
MEDIA_VOLUME_TOPIC = "gofer/{device_id}/media_player/volume"
MEDIA_COMMAND_TOPIC = "gofer/{device_id}/media_player/cmd"
MEDIA_VOLUME_SET_TOPIC = "gofer/{device_id}/media_player/volume_set"
