"""
homeassistant.remote
~~~~~~~~~~~~~~~~~~~~

A module containing drop in replacements for core parts that will interface
with a remote instance of home assistant.

If a connection error occurs while communicating with the API a
HomeAssistantError will be raised.
"""

import threading
import logging
import json
import urllib.parse

import requests

import homeassistant as ha
import homeassistant.components.httpinterface as hah

METHOD_GET = "get"
METHOD_POST = "post"


def _setup_call_api(host, port, api_password):
    """ Helper method to setup a call api method. """
    port = port or hah.SERVER_PORT

    base_url = "http://{}:{}".format(host, port)

    def _call_api(method, path, data=None):
        """ Makes a call to the Home Assistant api. """
        data = data or {}
        data['api_password'] = api_password

        url = urllib.parse.urljoin(base_url, path)

        try:
            if method == METHOD_GET:
                return requests.get(url, params=data)
            else:
                return requests.request(method, url, data=data)

        except requests.exceptions.ConnectionError:
            logging.getLogger(__name__).exception("Error connecting to server")
            raise ha.HomeAssistantError("Error connecting to server")

    return _call_api


class JSONEncoder(json.JSONEncoder):
    """ JSONEncoder that supports Home Assistant objects. """

    def default(self, obj):  # pylint: disable=method-hidden
        """ Checks if Home Assistat object and encodes if possible.
        Else hand it off to original method. """
        if isinstance(obj, ha.State):
            return obj.as_dict()

        return json.JSONEncoder.default(self, obj)


class Bus(object):
    """ Drop-in replacement for a normal bus that will forward interaction to
    a remote bus.
    """

    def __init__(self, host, api_password, port=None):
        self.logger = logging.getLogger(__name__)

        self._call_api = _setup_call_api(host, port, api_password)

    @property
    def services(self):
        """ List the available services. """
        try:
            req = self._call_api(METHOD_GET, hah.URL_API_SERVICES)

            if req.status_code == 200:
                data = req.json()

                return data['services']

            else:
                raise ha.HomeAssistantError(
                    "Got unexpected result (3): {}.".format(req.text))

        except ValueError:  # If req.json() can't parse the json
            self.logger.exception("Bus:Got unexpected result")
            raise ha.HomeAssistantError(
                "Got unexpected result: {}".format(req.text))

        except KeyError:  # If not all expected keys are in the returned JSON
            self.logger.exception("Bus:Got unexpected result (2)")
            raise ha.HomeAssistantError(
                "Got unexpected result (2): {}".format(req.text))

    @property
    def event_listeners(self):
        """ List of events that is being listened for. """
        try:
            req = self._call_api(METHOD_GET, hah.URL_API_EVENTS)

            if req.status_code == 200:
                data = req.json()

                return data['event_listeners']

            else:
                raise ha.HomeAssistantError(
                    "Got unexpected result (3): {}.".format(req.text))

        except ValueError:  # If req.json() can't parse the json
            self.logger.exception("Bus:Got unexpected result")
            raise ha.HomeAssistantError(
                "Got unexpected result: {}".format(req.text))

        except KeyError:  # If not all expected keys are in the returned JSON
            self.logger.exception("Bus:Got unexpected result (2)")
            raise ha.HomeAssistantError(
                "Got unexpected result (2): {}".format(req.text))

    def call_service(self, domain, service, service_data=None):
        """ Calls a service. """

        if service_data:
            data = {'service_data': json.dumps(service_data)}
        else:
            data = None

        req = self._call_api(METHOD_POST,
                             hah.URL_API_SERVICES_SERVICE.format(
                                 domain, service),
                             data)

        if req.status_code != 200:
            error = "Error calling service: {} - {}".format(
                    req.status_code, req.text)

            self.logger.error("Bus:{}".format(error))

            if req.status_code == 400:
                raise ha.ServiceDoesNotExistError(error)
            else:
                raise ha.HomeAssistantError(error)

    def register_service(self, domain, service, service_callback):
        """ Not implemented for remote bus.

        Will throw NotImplementedError. """
        raise NotImplementedError

    def fire_event(self, event_type, event_data=None):
        """ Fire an event. """

        if event_data:
            data = {'event_data': json.dumps(event_data, cls=JSONEncoder)}
        else:
            data = None

        req = self._call_api(METHOD_POST,
                             hah.URL_API_EVENTS_EVENT.format(event_type),
                             data)

        if req.status_code != 200:
            error = "Error firing event: {} - {}".format(
                    req.status_code, req.text)

            self.logger.error("Bus:{}".format(error))
            raise ha.HomeAssistantError(error)

    def has_service(self, domain, service):
        """ Not implemented for remote bus.

        Will throw NotImplementedError. """
        raise NotImplementedError

    def listen_event(self, event_type, listener):
        """ Not implemented for remote bus.

        Will throw NotImplementedError. """
        raise NotImplementedError

    def remove_event_listener(self, event_type, listener):
        """ Not implemented for remote bus.

        Will throw NotImplementedError. """

        raise NotImplementedError


class StateMachine(object):
    """ Drop-in replacement for a normal statemachine that communicates with a
    remote statemachine.
    """

    def __init__(self, host, api_password, port=None):
        self._call_api = _setup_call_api(host, port, api_password)

        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    @property
    def entity_ids(self):
        """ List of entity ids which states are being tracked. """

        try:
            req = self._call_api(METHOD_GET, hah.URL_API_STATES)

            return req.json()['entity_ids']

        except requests.exceptions.ConnectionError:
            self.logger.exception("StateMachine:Error connecting to server")
            return []

        except ValueError:  # If req.json() can't parse the json
            self.logger.exception("StateMachine:Got unexpected result")
            return []

        except KeyError:  # If 'entity_ids' key not in parsed json
            self.logger.exception("StateMachine:Got unexpected result (2)")
            return []

    def remove_entity(self, entity_id):
        """ This method is not implemented for remote statemachine.

        Throws NotImplementedError. """

        raise NotImplementedError

    def set_state(self, entity_id, new_state, attributes=None):
        """ Set the state of a entity, add entity if it does not exist.

        Attributes is an optional dict to specify attributes of this state. """

        attributes = attributes or {}

        self.lock.acquire()

        data = {'new_state': new_state,
                'attributes': json.dumps(attributes)}

        try:
            req = self._call_api(METHOD_POST,
                                 hah.URL_API_STATES_ENTITY.format(entity_id),
                                 data)

            if req.status_code != 201:
                error = "Error changing state: {} - {}".format(
                        req.status_code, req.text)

                self.logger.error("StateMachine:{}".format(error))
                raise ha.HomeAssistantError(error)

        except requests.exceptions.ConnectionError:
            self.logger.exception("StateMachine:Error connecting to server")
            raise ha.HomeAssistantError("Error connecting to server")

        finally:
            self.lock.release()

    def get_state(self, entity_id):
        """ Returns the state of the specified entity. """

        try:
            req = self._call_api(METHOD_GET,
                                 hah.URL_API_STATES_ENTITY.format(entity_id))

            if req.status_code == 200:
                data = req.json()

                return ha.State.from_dict(data)

            elif req.status_code == 422:
                # Entity does not exist
                return None

            else:
                raise ha.HomeAssistantError(
                    "Got unexpected result (3): {}.".format(req.text))

        except requests.exceptions.ConnectionError:
            self.logger.exception("StateMachine:Error connecting to server")
            raise ha.HomeAssistantError("Error connecting to server")

        except ValueError:  # If req.json() can't parse the json
            self.logger.exception("StateMachine:Got unexpected result")
            raise ha.HomeAssistantError(
                "Got unexpected result: {}".format(req.text))

        except KeyError:  # If not all expected keys are in the returned JSON
            self.logger.exception("StateMachine:Got unexpected result (2)")
            raise ha.HomeAssistantError(
                "Got unexpected result (2): {}".format(req.text))

    def is_state(self, entity_id, state):
        """ Returns True if entity exists and is specified state. """
        try:
            return self.get_state(entity_id).state == state
        except AttributeError:
            # get_state returned None
            return False
