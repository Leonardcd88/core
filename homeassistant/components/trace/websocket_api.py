"""Websocket API for automation."""
import json

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import (
    DATA_DISPATCHER,
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.script import (
    SCRIPT_BREAKPOINT_HIT,
    SCRIPT_DEBUG_CONTINUE_ALL,
    breakpoint_clear,
    breakpoint_clear_all,
    breakpoint_list,
    breakpoint_set,
    debug_continue,
    debug_step,
    debug_stop,
)

from .const import DATA_TRACE
from .utils import TraceJSONEncoder

# mypy: allow-untyped-calls, allow-untyped-defs

TRACE_DOMAINS = ("automation", "script")


@callback
def async_setup(hass: HomeAssistant) -> None:
    """Set up the websocket API."""
    websocket_api.async_register_command(hass, websocket_trace_get)
    websocket_api.async_register_command(hass, websocket_trace_list)
    websocket_api.async_register_command(hass, websocket_trace_contexts)
    websocket_api.async_register_command(hass, websocket_breakpoint_clear)
    websocket_api.async_register_command(hass, websocket_breakpoint_list)
    websocket_api.async_register_command(hass, websocket_breakpoint_set)
    websocket_api.async_register_command(hass, websocket_debug_continue)
    websocket_api.async_register_command(hass, websocket_debug_step)
    websocket_api.async_register_command(hass, websocket_debug_stop)
    websocket_api.async_register_command(hass, websocket_subscribe_breakpoint_events)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/get",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_trace_get(hass, connection, msg):
    """Get an script or automation trace."""
    key = (msg["domain"], msg["item_id"])
    run_id = msg["run_id"]

    try:
        trace = hass.data[DATA_TRACE][key][run_id]
    except KeyError:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "The trace could not be found"
        )
        return

    message = websocket_api.messages.result_message(msg["id"], trace)

    connection.send_message(json.dumps(message, cls=TraceJSONEncoder, allow_nan=False))


def get_debug_traces(hass, key):
    """Return a serializable list of debug traces for an script or automation."""
    traces = []

    for trace in hass.data[DATA_TRACE].get(key, {}).values():
        traces.append(trace.as_short_dict())

    return traces


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/list",
        vol.Required("domain", "id"): vol.In(TRACE_DOMAINS),
        vol.Optional("item_id", "id"): str,
    }
)
def websocket_trace_list(hass, connection, msg):
    """Summarize script and automation traces."""
    domain = msg["domain"]
    key = (domain, msg["item_id"]) if "item_id" in msg else None

    if not key:
        traces = []
        for key in hass.data[DATA_TRACE]:
            if key[0] == domain:
                traces.extend(get_debug_traces(hass, key))
    else:
        traces = get_debug_traces(hass, key)

    connection.send_result(msg["id"], traces)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/contexts",
        vol.Inclusive("domain", "id"): vol.In(TRACE_DOMAINS),
        vol.Inclusive("item_id", "id"): str,
    }
)
def websocket_trace_contexts(hass, connection, msg):
    """Retrieve contexts we have traces for."""
    key = (msg["domain"], msg["item_id"]) if "item_id" in msg else None

    if key is not None:
        values = {key: hass.data[DATA_TRACE].get(key, {})}
    else:
        values = hass.data[DATA_TRACE]

    contexts = {
        trace.context.id: {"run_id": trace.run_id, "domain": key[0], "item_id": key[1]}
        for key, traces in values.items()
        for trace in traces.values()
    }

    connection.send_result(msg["id"], contexts)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/breakpoint/set",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("node"): str,
        vol.Optional("run_id"): str,
    }
)
def websocket_breakpoint_set(hass, connection, msg):
    """Set breakpoint."""
    key = (msg["domain"], msg["item_id"])
    node = msg["node"]
    run_id = msg.get("run_id")

    if (
        SCRIPT_BREAKPOINT_HIT not in hass.data.get(DATA_DISPATCHER, {})
        or not hass.data[DATA_DISPATCHER][SCRIPT_BREAKPOINT_HIT]
    ):
        raise HomeAssistantError("No breakpoint subscription")

    result = breakpoint_set(hass, key, run_id, node)
    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/breakpoint/clear",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("node"): str,
        vol.Optional("run_id"): str,
    }
)
def websocket_breakpoint_clear(hass, connection, msg):
    """Clear breakpoint."""
    key = (msg["domain"], msg["item_id"])
    node = msg["node"]
    run_id = msg.get("run_id")

    result = breakpoint_clear(hass, key, run_id, node)

    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "trace/debug/breakpoint/list"})
def websocket_breakpoint_list(hass, connection, msg):
    """List breakpoints."""
    breakpoints = breakpoint_list(hass)
    for _breakpoint in breakpoints:
        _breakpoint["domain"], _breakpoint["item_id"] = _breakpoint.pop("key")

    connection.send_result(msg["id"], breakpoints)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "trace/debug/breakpoint/subscribe"}
)
def websocket_subscribe_breakpoint_events(hass, connection, msg):
    """Subscribe to breakpoint events."""

    @callback
    def breakpoint_hit(key, run_id, node):
        """Forward events to websocket."""
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "domain": key[0],
                    "item_id": key[1],
                    "run_id": run_id,
                    "node": node,
                },
            )
        )

    remove_signal = async_dispatcher_connect(
        hass, SCRIPT_BREAKPOINT_HIT, breakpoint_hit
    )

    @callback
    def unsub():
        """Unsubscribe from breakpoint events."""
        remove_signal()
        if (
            SCRIPT_BREAKPOINT_HIT not in hass.data.get(DATA_DISPATCHER, {})
            or not hass.data[DATA_DISPATCHER][SCRIPT_BREAKPOINT_HIT]
        ):
            breakpoint_clear_all(hass)
            async_dispatcher_send(hass, SCRIPT_DEBUG_CONTINUE_ALL)

    connection.subscriptions[msg["id"]] = unsub

    connection.send_message(websocket_api.result_message(msg["id"]))


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/continue",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_debug_continue(hass, connection, msg):
    """Resume execution of halted script or automation."""
    key = (msg["domain"], msg["item_id"])
    run_id = msg["run_id"]

    result = debug_continue(hass, key, run_id)

    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/step",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_debug_step(hass, connection, msg):
    """Single step a halted script or automation."""
    key = (msg["domain"], msg["item_id"])
    run_id = msg["run_id"]

    result = debug_step(hass, key, run_id)

    connection.send_result(msg["id"], result)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "trace/debug/stop",
        vol.Required("domain"): vol.In(TRACE_DOMAINS),
        vol.Required("item_id"): str,
        vol.Required("run_id"): str,
    }
)
def websocket_debug_stop(hass, connection, msg):
    """Stop a halted script or automation."""
    key = (msg["domain"], msg["item_id"])
    run_id = msg["run_id"]

    result = debug_stop(hass, key, run_id)

    connection.send_result(msg["id"], result)
