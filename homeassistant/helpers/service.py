"""Service calling related helpers."""
import functools
import logging

from homeassistant.util import split_entity_id
from homeassistant.const import ATTR_ENTITY_ID

HASS = None

CONF_SERVICE = 'service'
CONF_SERVICE_ENTITY_ID = 'entity_id'
CONF_SERVICE_DATA = 'data'

_LOGGER = logging.getLogger(__name__)


def _callback(action, *args, **kwargs):
    """ adds HASS to callback arguments """
    action(HASS, *args, **kwargs)


def service(domain, service_name):
    """ Decorator factory to register a service """

    def register_service_decorator(action):
        """ Decorator to register a service """
        HASS.services.register(domain, service_name,
                               functools.partial(_callback, action))
        return action

    return register_service_decorator


def call_from_config(hass, config, blocking=False):
    """Call a service based on a config hash."""
    if not isinstance(config, dict) or CONF_SERVICE not in config:
        _LOGGER.error('Missing key %s: %s', CONF_SERVICE, config)
        return

    try:
        domain, service_name = split_entity_id(config[CONF_SERVICE])
    except ValueError:
        _LOGGER.error('Invalid service specified: %s', config[CONF_SERVICE])
        return

    service_data = config.get(CONF_SERVICE_DATA)

    if service_data is None:
        service_data = {}
    elif isinstance(service_data, dict):
        service_data = dict(service_data)
    else:
        _LOGGER.error("%s should be a dictionary", CONF_SERVICE_DATA)
        service_data = {}

    entity_id = config.get(CONF_SERVICE_ENTITY_ID)
    if isinstance(entity_id, str):
        service_data[ATTR_ENTITY_ID] = [ent.strip() for ent in
                                        entity_id.split(",")]
    elif entity_id is not None:
        service_data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(domain, service_name, service_data, blocking)
