"""Config flow to configure the devolo home control integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.typing import DiscoveryInfoType

from . import configure_mydevolo
from .const import (  # pylint:disable=unused-import
    CONF_MYDEVOLO,
    DEFAULT_MYDEVOLO,
    DOMAIN,
    SUPPORTED_MODEL_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class DevoloHomeControlFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a devolo HomeControl config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def __init__(self):
        """Initialize devolo Home Control flow."""
        self.data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if self.show_advanced_options:
            self.data_schema[
                vol.Required(CONF_MYDEVOLO, default=DEFAULT_MYDEVOLO)
            ] = str
        if user_input is None:
            return self._show_form(user_input)
        return await self._connect_mydevolo(user_input)

    async def async_step_zeroconf(self, discovery_info: DiscoveryInfoType):
        """Handle zeroconf discovery."""
        # Check if it is a gateway
        if discovery_info.get("properties", {}).get("MT") in SUPPORTED_MODEL_TYPES:
            await self._async_handle_discovery_without_unique_id()
            return await self.async_step_zeroconf_confirm()
        return self.async_abort(reason="Not a devolo Home Control gateway.")

    async def async_step_zeroconf_confirm(self, user_input=None):
        """Handle a flow initiated by zeroconf."""
        if user_input is None:
            return self._show_form(step_id="zeroconf_confirm")
        return await self._connect_mydevolo(user_input)

    async def _connect_mydevolo(self, user_input):
        """Connect to mydevolo."""
        mydevolo = configure_mydevolo(conf=user_input)
        credentials_valid = await self.hass.async_add_executor_job(
            mydevolo.credentials_valid
        )
        if not credentials_valid:
            return self._show_form({"base": "invalid_auth"})
        _LOGGER.debug("Credentials valid")
        uuid = await self.hass.async_add_executor_job(mydevolo.uuid)
        await self.async_set_unique_id(uuid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="devolo Home Control",
            data={
                CONF_PASSWORD: mydevolo.password,
                CONF_USERNAME: mydevolo.user,
                CONF_MYDEVOLO: mydevolo.url,
            },
        )

    @callback
    def _show_form(self, errors=None, step_id="user"):
        """Show the form to the user."""
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(self.data_schema),
            errors=errors if errors else {},
        )
