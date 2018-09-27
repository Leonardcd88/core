"""Provide configuration end points for scripts."""
import asyncio

from homeassistant.components.config import EditKeyBasedConfigView
from homeassistant.components.script import DOMAIN, SCRIPT_ENTRY_SCHEMA
from homeassistant.const import SERVICE_RELOAD
import homeassistant.helpers.config_validation as cv


CONFIG_PATH = 'scripts.yaml'


@asyncio.coroutine
def async_setup(hass):
    """Set up the script config API."""
    async def hook(hass):
        """post_write_hook for Config View that reloads scripts."""
        await hass.services.async_call(DOMAIN, SERVICE_RELOAD)

    hass.http.register_view(EditKeyBasedConfigView(
        'script', 'config', CONFIG_PATH, cv.slug, SCRIPT_ENTRY_SCHEMA,
        post_write_hook=hook
    ))
    return True
