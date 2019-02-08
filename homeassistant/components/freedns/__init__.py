"""
Integrate with FreeDNS Dynamic DNS service at freedns.afraid.org.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/freedns/
"""
import asyncio
from datetime import timedelta
import logging

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.const import (CONF_URL, CONF_ACCESS_TOKEN,
                                 CONF_UPDATE_INTERVAL, CONF_SCAN_INTERVAL)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'freedns'

DEFAULT_INTERVAL = timedelta(minutes=10)

TIMEOUT = 10
UPDATE_URL = 'https://freedns.afraid.org/dynamic/update.php'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(
        vol.Schema({
            vol.Exclusive(CONF_URL, DOMAIN): cv.string,
            vol.Exclusive(CONF_ACCESS_TOKEN, DOMAIN): cv.string,
            vol.Optional(CONF_UPDATE_INTERVAL):
                vol.All(cv.time_period, cv.positive_timedelta),
            vol.Optional(CONF_SCAN_INTERVAL):
                vol.All(cv.time_period, cv.positive_timedelta),
        }),
        cv.deprecated(
            CONF_UPDATE_INTERVAL,
            replacement_key=CONF_SCAN_INTERVAL,
            invalidation_version='1.0.0',
            default=DEFAULT_INTERVAL
        )
    )
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Initialize the FreeDNS component."""
    conf = config[DOMAIN]
    url = conf.get(CONF_URL)
    auth_token = conf.get(CONF_ACCESS_TOKEN)
    update_interval = conf[CONF_SCAN_INTERVAL]

    session = hass.helpers.aiohttp_client.async_get_clientsession()

    result = await _update_freedns(
        hass, session, url, auth_token)

    if result is False:
        return False

    async def update_domain_callback(now):
        """Update the FreeDNS entry."""
        await _update_freedns(hass, session, url, auth_token)

    hass.helpers.event.async_track_time_interval(
        update_domain_callback, update_interval)

    return True


async def _update_freedns(hass, session, url, auth_token):
    """Update FreeDNS."""
    params = None

    if url is None:
        url = UPDATE_URL

    if auth_token is not None:
        params = {}
        params[auth_token] = ""

    try:
        with async_timeout.timeout(TIMEOUT, loop=hass.loop):
            resp = await session.get(url, params=params)
            body = await resp.text()

            if "has not changed" in body:
                # IP has not changed.
                _LOGGER.debug("FreeDNS update skipped: IP has not changed")
                return True

            if "ERROR" not in body:
                _LOGGER.debug("Updating FreeDNS was successful: %s", body)
                return True

            if "Invalid update URL" in body:
                _LOGGER.error("FreeDNS update token is invalid")
            else:
                _LOGGER.warning("Updating FreeDNS failed: %s", body)

    except aiohttp.ClientError:
        _LOGGER.warning("Can't connect to FreeDNS API")

    except asyncio.TimeoutError:
        _LOGGER.warning("Timeout from FreeDNS API at %s", url)

    return False
