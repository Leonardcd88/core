"""
homeassistant.components.chromecast
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides functionality to interact with Chromecasts.
"""
import logging

import homeassistant as ha
import homeassistant.util as util
import homeassistant.components as components

DOMAIN = 'chromecast'

SERVICE_YOUTUBE_VIDEO = 'play_youtube_video'

ENTITY_ID_FORMAT = DOMAIN + '.{}'
STATE_NO_APP = 'no_app'

ATTR_FRIENDLY_NAME = 'friendly_name'
ATTR_HOST = 'host'
ATTR_STATE = 'state'
ATTR_OPTIONS = 'options'
ATTR_MEDIA_STATE = 'media_state'
ATTR_MEDIA_CONTENT_ID = 'media_content_id'
ATTR_MEDIA_TITLE = 'media_title'
ATTR_MEDIA_ARTIST = 'media_artist'
ATTR_MEDIA_ALBUM = 'media_album'
ATTR_MEDIA_IMAGE_URL = 'media_image_url'
ATTR_MEDIA_VOLUME = 'media_volume'
ATTR_MEDIA_DURATION = 'media_duration'

MEDIA_STATE_UNKNOWN = 'unknown'
MEDIA_STATE_PLAYING = 'playing'
MEDIA_STATE_STOPPED = 'stopped'


def is_on(statemachine, entity_id=None):
    """ Returns true if specified ChromeCast entity_id is on.
    Will check all chromecasts if no entity_id specified. """

    entity_ids = [entity_id] if entity_id \
        else util.filter_entity_ids(statemachine.entity_ids, DOMAIN)

    return any(not statemachine.is_state(entity_id, STATE_NO_APP)
               for entity_id in entity_ids)


def volume_up(bus, entity_id=None):
    """ Send the chromecast the command for volume up. """
    data = {components.ATTR_ENTITY_ID: entity_id} if entity_id else {}

    bus.call_service(DOMAIN, components.SERVICE_VOLUME_UP, data)


def volume_down(bus, entity_id=None):
    """ Send the chromecast the command for volume down. """
    data = {components.ATTR_ENTITY_ID: entity_id} if entity_id else {}

    bus.call_service(DOMAIN, components.SERVICE_VOLUME_DOWN, data)


def media_play_pause(bus, entity_id=None):
    """ Send the chromecast the command for play/pause. """
    data = {components.ATTR_ENTITY_ID: entity_id} if entity_id else {}

    bus.call_service(DOMAIN, components.SERVICE_MEDIA_PLAY_PAUSE, data)


def media_next_track(bus, entity_id=None):
    """ Send the chromecast the command for next track. """
    data = {components.ATTR_ENTITY_ID: entity_id} if entity_id else {}

    bus.call_service(DOMAIN, components.SERVICE_MEDIA_NEXT_TRACK, data)


def media_prev_track(bus, entity_id=None):
    """ Send the chromecast the command for prev track. """
    data = {components.ATTR_ENTITY_ID: entity_id} if entity_id else {}

    bus.call_service(DOMAIN, components.SERVICE_MEDIA_PREV_TRACK, data)


# pylint: disable=too-many-locals, too-many-branches
def setup(bus, statemachine):
    """ Listen for chromecast events. """
    logger = logging.getLogger(__name__)

    try:
        import pychromecast
    except ImportError:
        logger.exception(("Failed to import pychromecast. "
                          "Did you maybe not install the 'pychromecast' "
                          "dependency?"))

        return False

    logger.info("Scanning for Chromecasts")
    hosts = pychromecast.discover_chromecasts()

    casts = {}

    for host in hosts:
        try:
            cast = pychromecast.PyChromecast(host)

            entity_id = ENTITY_ID_FORMAT.format(
                            util.slugify(cast.device.friendly_name))

            casts[entity_id] = cast

        except pychromecast.ConnectionError:
            pass

    if not casts:
        logger.error("Could not find Chromecasts")
        return False

    def update_chromecast_state(entity_id, chromecast):
        """ Retrieve state of Chromecast and update statemachine. """
        chromecast.refresh()

        status = chromecast.app

        state_attr = {ATTR_HOST: chromecast.host,
                      ATTR_FRIENDLY_NAME: chromecast.device.friendly_name}

        if status and status.app_id != pychromecast.APP_ID['HOME']:
            state = status.app_id

            ramp = chromecast.get_protocol(pychromecast.PROTOCOL_RAMP)

            if ramp and ramp.state != pychromecast.RAMP_STATE_UNKNOWN:

                if ramp.state == pychromecast.RAMP_STATE_PLAYING:
                    state_attr[ATTR_MEDIA_STATE] = MEDIA_STATE_PLAYING
                else:
                    state_attr[ATTR_MEDIA_STATE] = MEDIA_STATE_STOPPED

                if ramp.content_id:
                    state_attr[ATTR_MEDIA_CONTENT_ID] = ramp.content_id

                if ramp.title:
                    state_attr[ATTR_MEDIA_TITLE] = ramp.title

                if ramp.artist:
                    state_attr[ATTR_MEDIA_ARTIST] = ramp.artist

                if ramp.album:
                    state_attr[ATTR_MEDIA_ALBUM] = ramp.album

                if ramp.image_url:
                    state_attr[ATTR_MEDIA_IMAGE_URL] = ramp.image_url

                if ramp.duration:
                    state_attr[ATTR_MEDIA_DURATION] = ramp.duration

                state_attr[ATTR_MEDIA_VOLUME] = ramp.volume
        else:
            state = STATE_NO_APP

        statemachine.set_state(entity_id, state, state_attr)

    def update_chromecast_states(time):  # pylint: disable=unused-argument
        """ Updates all chromecast states. """
        logger.info("Updating Chromecast status")

        for entity_id, cast in casts.items():
            update_chromecast_state(entity_id, cast)

    def _service_to_entities(service):
        """ Helper method to get entities from service. """
        entity_id = service.data.get(components.ATTR_ENTITY_ID)

        if entity_id:
            cast = casts.get(entity_id)

            if cast:
                yield entity_id, cast

        else:
            for item in casts.items():
                yield item

    def turn_off_service(service):
        """ Service to exit any running app on the specified ChromeCast and
        shows idle screen. Will quit all ChromeCasts if nothing specified.
        """
        for entity_id, cast in _service_to_entities(service):
            cast.quit_app()
            update_chromecast_state(entity_id, cast)

    def volume_up_service(service):
        """ Service to send the chromecast the command for volume up. """
        for _, cast in _service_to_entities(service):
            ramp = cast.get_protocol(pychromecast.PROTOCOL_RAMP)

            if ramp:
                ramp.volume_up()

    def volume_down_service(service):
        """ Service to send the chromecast the command for volume down. """
        for _, cast in _service_to_entities(service):
            ramp = cast.get_protocol(pychromecast.PROTOCOL_RAMP)

            if ramp:
                ramp.volume_down()

    def media_play_pause_service(service):
        """ Service to send the chromecast the command for play/pause. """
        for _, cast in _service_to_entities(service):
            ramp = cast.get_protocol(pychromecast.PROTOCOL_RAMP)

            if ramp:
                ramp.playpause()

    def media_next_track_service(service):
        """ Service to send the chromecast the command for next track. """
        for entity_id, cast in _service_to_entities(service):
            ramp = cast.get_protocol(pychromecast.PROTOCOL_RAMP)

            if ramp:
                ramp.next()
                update_chromecast_state(entity_id, cast)

    def play_youtube_video_service(service, video_id):
        """ Plays specified video_id on the Chromecast's YouTube channel. """
        if video_id:  # if service.data.get('video') returned None
            for entity_id, cast in _service_to_entities(service):
                pychromecast.play_youtube_video(video_id, cast.host)
                update_chromecast_state(entity_id, cast)

    ha.track_time_change(bus, update_chromecast_states)

    bus.register_service(DOMAIN, components.SERVICE_TURN_OFF,
                         turn_off_service)

    bus.register_service(DOMAIN, components.SERVICE_VOLUME_UP,
                         volume_up_service)

    bus.register_service(DOMAIN, components.SERVICE_VOLUME_DOWN,
                         volume_down_service)

    bus.register_service(DOMAIN, components.SERVICE_MEDIA_PLAY_PAUSE,
                         media_play_pause_service)

    bus.register_service(DOMAIN, components.SERVICE_MEDIA_NEXT_TRACK,
                         media_next_track_service)

    bus.register_service(DOMAIN, "start_fireplace",
                         lambda service:
                         play_youtube_video_service(service, "eyU3bRy2x44"))

    bus.register_service(DOMAIN, "start_epic_sax",
                         lambda service:
                         play_youtube_video_service(service, "kxopViU98Xo"))

    bus.register_service(DOMAIN, SERVICE_YOUTUBE_VIDEO,
                         lambda service:
                         play_youtube_video_service(service,
                                                    service.data.get('video')))

    update_chromecast_states(None)

    return True
