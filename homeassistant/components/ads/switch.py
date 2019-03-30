"""Support for ADS switch platform."""
import logging
import asyncio
import async_timeout

import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity

from . import CONF_ADS_VAR, DATA_ADS

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['ads']

DEFAULT_NAME = 'ADS Switch'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ADS_VAR): cv.string,
    vol.Optional(CONF_NAME): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up switch platform for ADS."""
    ads_hub = hass.data.get(DATA_ADS)

    name = config.get(CONF_NAME)
    ads_var = config.get(CONF_ADS_VAR)

    add_entities([AdsSwitch(ads_hub, name, ads_var)])


class AdsSwitch(ToggleEntity):
    """Representation of an ADS switch device."""

    def __init__(self, ads_hub, name, ads_var):
        """Initialize the AdsSwitch entity."""
        self._ads_hub = ads_hub
        self._on_state = None
        self._name = name
        self._unique_id = ads_var
        self.ads_var = ads_var
        self._event = None

    async def async_added_to_hass(self):
        """Register device notification."""
        def update(name, value):
            """Handle device notification."""
            _LOGGER.debug("Variable %s changed its value to %d", name, value)
            self._on_state = value
            asyncio.run_coroutine_threadsafe(async_event_set(), self.hass.loop)
            self.schedule_update_ha_state()

        async def async_event_set():
            """Set event in async context."""
            self._event.set()

        self._event = asyncio.Event()

        await self.hass.async_add_executor_job(
            self._ads_hub.add_device_notification,
            self.ads_var, self._ads_hub.PLCTYPE_BOOL, update)
        try:
            with async_timeout.timeout(10):
                await self._event.wait()
        except asyncio.TimeoutError:
            _LOGGER.debug('Variable %s: Timeout during first update',
                          self.ads_var)

    @property
    def is_on(self):
        """Return if the switch is turned on."""
        return self._on_state

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self):
        """Return an unique identifier for this entity."""
        return self._unique_id

    @property
    def should_poll(self):
        """Return False because entity pushes its state to HA."""
        return False

    @property
    def available(self):
        """Return False if state has not been updated yet."""
        return self._on_state is not None

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._ads_hub.write_by_name(
            self.ads_var, True, self._ads_hub.PLCTYPE_BOOL)

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self._ads_hub.write_by_name(
            self.ads_var, False, self._ads_hub.PLCTYPE_BOOL)
