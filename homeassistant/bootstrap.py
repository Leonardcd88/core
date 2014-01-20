"""
Provides methods to bootstrap a home assistant instance.
"""

import ConfigParser
import logging

import homeassistant as ha
from homeassistant.components import (general, chromecast,
                                      device_sun_light_trigger, device_tracker,
                                      downloader, keyboard, light, sun,
                                      browser, httpinterface, group)


# pylint: disable=too-many-branches,too-many-locals,too-many-statements
def from_config_file(config_path):
    """ Starts home assistant with all possible functionality
        based on a config file. """

    logger = logging.getLogger(__name__)

    statusses = []

    # Read config
    config = ConfigParser.SafeConfigParser()
    config.read(config_path)

    # Init core
    bus = ha.Bus()
    statemachine = ha.StateMachine(bus)

    has_opt = config.has_option
    get_opt = config.get
    has_section = config.has_section
    add_status = lambda name, result: statusses.append((name, result))

    def get_opt_safe(section, option, default=None):
        """ Failure proof option retriever. """
        try:
            return config.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    # Device scanner
    dev_scan = None

    try:
        # For the error message if not all option fields exist
        opt_fields = "host, username, password"

        if has_section('device_tracker.tomato'):
            dev_scan_name = "Tomato"
            opt_fields += ", http_id"

            dev_scan = device_tracker.TomatoDeviceScanner(
                get_opt('device_tracker.tomato', 'host'),
                get_opt('device_tracker.tomato', 'username'),
                get_opt('device_tracker.tomato', 'password'),
                get_opt('device_tracker.tomato', 'http_id'))

        elif has_section('device_tracker.netgear'):
            dev_scan_name = "Netgear"

            dev_scan = device_tracker.NetgearDeviceScanner(
                get_opt('device_tracker.netgear', 'host'),
                get_opt('device_tracker.netgear', 'username'),
                get_opt('device_tracker.netgear', 'password'))

    except ConfigParser.NoOptionError:
        # If one of the options didn't exist
        logger.exception(("Error initializing {}DeviceScanner, "
                          "could not find one of the following config "
                          "options: {}".format(dev_scan_name, opt_fields)))

        add_status("Device Scanner - {}".format(dev_scan_name), False)

    if dev_scan:
        add_status("Device Scanner - {}".format(dev_scan_name),
                   dev_scan.success_init)

        if not dev_scan.success_init:
            dev_scan = None

    # Device Tracker
    if dev_scan:
        device_tracker.DeviceTracker(bus, statemachine, dev_scan)

        add_status("Device Tracker", True)

    # Sun tracker
    if has_opt("common", "latitude") and \
       has_opt("common", "longitude"):

        add_status("Weather - Ephem",
                   sun.setup(
                       bus, statemachine,
                       get_opt("common", "latitude"),
                       get_opt("common", "longitude")))

    # Chromecast
    if has_opt("chromecast", "host"):
        chromecast_started = chromecast.setup(bus, statemachine,
                                              get_opt("chromecast", "host"))

        add_status("Chromecast", chromecast_started)
    else:
        chromecast_started = False

    # Light control
    if has_section("light.hue"):
        light_control = light.HueLightControl(get_opt_safe("hue", "host"))

        add_status("Light Control - Hue", light_control.success_init)

        light.setup(bus, statemachine, light_control)
    else:
        light_control = None

    if has_opt("downloader", "download_dir"):
        add_status("Downloader", downloader.setup(
            bus, get_opt("downloader", "download_dir")))

    # Currently only works with Chromecast or Light_Control
    if chromecast_started or light_control:
        add_status("General", general.setup(bus, statemachine))

    add_status("Browser", browser.setup(bus))

    add_status("Media Buttons", keyboard.setup(bus))

    # Init HTTP interface
    if has_opt("httpinterface", "api_password"):
        httpinterface.HTTPInterface(
            bus, statemachine,
            get_opt("httpinterface", "api_password"))

        add_status("HTTPInterface", True)

    # Init groups
    if has_section("groups"):
        for name, entity_ids in config.items("groups"):
            add_status("Group - {}".format(name),
                       group.setup(bus, statemachine, name,
                                   entity_ids.split(",")))

    # Light trigger
    if light_control:
        light_group = get_opt_safe("device_sun_light_trigger", "light_group")

        add_status("Light Trigger",
                   device_sun_light_trigger.setup(bus, statemachine,
                                                  light_group))

    for component, success_init in statusses:
        status = "initialized" if success_init else "Failed to initialize"

        logger.info("{}: {}".format(component, status))

    ha.start_home_assistant(bus)
