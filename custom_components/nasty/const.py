"""Constants for the NASty integration."""

from datetime import timedelta

DOMAIN = "nasty"

CONF_API_TOKEN = "api_token"
CONF_ENABLE_CONTROLS = "enable_controls"
CONF_URL = "url"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_ENABLE_CONTROLS = False
DEFAULT_VERIFY_SSL = True

FAST_UPDATE_INTERVAL = timedelta(seconds=30)
STORAGE_UPDATE_INTERVAL = timedelta(minutes=5)
