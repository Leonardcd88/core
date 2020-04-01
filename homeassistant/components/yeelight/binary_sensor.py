"""Sensor platform support for yeelight."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DATA_UPDATED, DATA_YEELIGHT

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Yeelight sensors."""
    if not discovery_info:
        return

    device = hass.data[DATA_YEELIGHT][discovery_info["host"]]

    if device.is_nightlight_supported:
        _LOGGER.debug("Adding nightlight mode sensor for %s", device.name)
        add_entities([YeelightNightlightModeSensor(device)])


class YeelightNightlightModeSensor(BinarySensorDevice):
    """Representation of a Yeelight nightlight mode sensor."""

    def __init__(self, device):
        """Initialize nightlight mode sensor."""
        self._device = device
        self._unsub_disp = None

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        self._unsub_disp = async_dispatcher_connect(
            self.hass,
            DATA_UPDATED.format(self._device.ipaddr),
            self.async_write_ha_state,
        )

    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self._unsub_disp()
        self._unsub_disp = None

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._device.name} nightlight"

    @property
    def is_on(self):
        """Return true if nightlight mode is on."""
        return self._device.is_nightlight_enabled
