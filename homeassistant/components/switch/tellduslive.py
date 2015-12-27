"""
homeassistant.components.switch.tellduslive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Tellstick switches using Tellstick Net and
the Telldus Live online service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tellduslive/

"""
import logging

from homeassistant.const import (STATE_ON, STATE_OFF, STATE_UNKNOWN)
from homeassistant.components import tellduslive
from homeassistant.helpers.entity import ToggleEntity

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ['tellduslive']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Find and return Tellstick switches. """
    switches = tellduslive.NETWORK.get_switches()
    add_devices([TelldusLiveSwitch(switch["name"],
                                   switch["id"])
                 for switch in switches if switch["type"] == "device"])


class TelldusLiveSwitch(ToggleEntity):
    """ Represents a Tellstick switch. """

    def __init__(self, name, switch_id):
        self._name = name
        self._id = switch_id
        self._state = STATE_UNKNOWN
        self.update()

    @property
    def should_poll(self):
        """ Tells Home Assistant to poll this entity. """
        return True

    @property
    def name(self):
        """ Returns the name of the switch if any. """
        return self._name

    def update(self):
        from tellcore.constants import (
            TELLSTICK_TURNON, TELLSTICK_TURNOFF)
        states = {TELLSTICK_TURNON:  STATE_ON,
                  TELLSTICK_TURNOFF: STATE_OFF}
        state = tellduslive.NETWORK.get_switch_state(self._id)
        self._state = states[state]

    @property
    def is_on(self):
        """ True if switch is on. """
        self.update()
        return self._state == STATE_ON

    def turn_on(self, **kwargs):
        """ Turns the switch on. """
        if tellduslive.NETWORK.turn_switch_on(self._id):
            self._state = STATE_ON

    def turn_off(self, **kwargs):
        """ Turns the switch off. """
        if tellduslive.NETWORK.turn_switch_off(self._id):
            self._state = STATE_OFF
