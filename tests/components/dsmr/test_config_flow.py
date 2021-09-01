"""Test the DSMR config flow."""
import asyncio
from itertools import chain, repeat
import os
from unittest.mock import DEFAULT, AsyncMock, MagicMock, patch, sentinel

import serial
import serial.tools.list_ports

from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.components.dsmr import DOMAIN, config_flow

from tests.common import MockConfigEntry

SERIAL_DATA = {"serial_id": "12345678", "serial_id_gas": "123456789"}
SERIAL_DATA_SWEDEN = {"serial_id": None, "serial_id_gas": None}


def com_port():
    """Mock of a serial port."""
    port = serial.tools.list_ports_common.ListPortInfo("/dev/ttyUSB1234")
    port.serial_number = "1234"
    port.manufacturer = "Virtual serial port"
    port.device = "/dev/ttyUSB1234"
    port.description = "Some serial port"

    return port


async def test_setup_network(hass, dsmr_connection_send_validate_fixture):
    """Test we can setup network."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"type": "Network"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_network"
    assert result["errors"] == {}

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "10.10.0.1", "port": 1234, "dsmr_version": "2.2"},
        )

    entry_data = {
        "host": "10.10.0.1",
        "port": 1234,
        "dsmr_version": "2.2",
    }

    assert result["type"] == "create_entry"
    assert result["title"] == "10.10.0.1:1234"
    assert result["data"] == {**entry_data, **SERIAL_DATA}


@patch("serial.tools.list_ports.comports", return_value=[com_port()])
async def test_setup_serial(com_mock, hass, dsmr_connection_send_validate_fixture):
    """Test we can setup serial."""
    port = com_port()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"type": "Serial"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial"
    assert result["errors"] == {}

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"port": port.device, "dsmr_version": "2.2"}
        )

    entry_data = {
        "port": port.device,
        "dsmr_version": "2.2",
    }

    assert result["type"] == "create_entry"
    assert result["title"] == port.device
    assert result["data"] == {**entry_data, **SERIAL_DATA}


@patch("serial.tools.list_ports.comports", return_value=[com_port()])
async def test_setup_serial_manual(
    com_mock, hass, dsmr_connection_send_validate_fixture
):
    """Test we can setup serial with manual entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"type": "Serial"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"port": "Enter Manually", "dsmr_version": "2.2"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial_manual_path"
    assert result["errors"] is None

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"port": "/dev/ttyUSB0"}
        )

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
    }

    assert result["type"] == "create_entry"
    assert result["title"] == "/dev/ttyUSB0"
    assert result["data"] == {**entry_data, **SERIAL_DATA}


@patch("serial.tools.list_ports.comports", return_value=[com_port()])
async def test_setup_serial_fail(com_mock, hass, dsmr_connection_send_validate_fixture):
    """Test failed serial connection."""
    (connection_factory, transport, protocol) = dsmr_connection_send_validate_fixture

    await setup.async_setup_component(hass, "persistent_notification", {})

    port = com_port()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # override the mock to have it fail the first time and succeed after
    first_fail_connection_factory = AsyncMock(
        return_value=(transport, protocol),
        side_effect=chain([serial.serialutil.SerialException], repeat(DEFAULT)),
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"type": "Serial"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.dsmr.config_flow.create_dsmr_reader",
        first_fail_connection_factory,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"port": port.device, "dsmr_version": "2.2"}
        )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial"
    assert result["errors"] == {"base": "cannot_connect"}


@patch("serial.tools.list_ports.comports", return_value=[com_port()])
async def test_setup_serial_wrong_telegram(
    com_mock, hass, dsmr_connection_send_validate_fixture
):
    """Test failed telegram data."""
    (connection_factory, transport, protocol) = dsmr_connection_send_validate_fixture

    await setup.async_setup_component(hass, "persistent_notification", {})

    port = com_port()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    protocol.telegram = {}

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"type": "Serial"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"port": port.device, "dsmr_version": "2.2"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "setup_serial"
    assert result["errors"] == {"base": "cannot_communicate"}


async def test_import_usb(hass, dsmr_connection_send_validate_fixture):
    """Test we can import."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "/dev/ttyUSB0"
    assert result["data"] == {**entry_data, **SERIAL_DATA}


async def test_import_usb_failed_connection(
    hass, dsmr_connection_send_validate_fixture
):
    """Test we can import."""
    (connection_factory, transport, protocol) = dsmr_connection_send_validate_fixture

    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    # override the mock to have it fail the first time and succeed after
    first_fail_connection_factory = AsyncMock(
        return_value=(transport, protocol),
        side_effect=chain([serial.serialutil.SerialException], repeat(DEFAULT)),
    )

    with patch(
        "homeassistant.components.dsmr.async_setup_entry", return_value=True
    ), patch(
        "homeassistant.components.dsmr.config_flow.create_dsmr_reader",
        first_fail_connection_factory,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


async def test_import_usb_no_data(hass, dsmr_connection_send_validate_fixture):
    """Test we can import."""
    (connection_factory, transport, protocol) = dsmr_connection_send_validate_fixture

    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    # override the mock to have it fail the first time and succeed after
    wait_closed = AsyncMock(
        return_value=(transport, protocol),
        side_effect=chain([asyncio.TimeoutError], repeat(DEFAULT)),
    )

    protocol.wait_closed = wait_closed

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_communicate"


async def test_import_usb_wrong_telegram(hass, dsmr_connection_send_validate_fixture):
    """Test we can import."""
    (connection_factory, transport, protocol) = dsmr_connection_send_validate_fixture

    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    protocol.telegram = {}

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_communicate"


async def test_import_network(hass, dsmr_connection_send_validate_fixture):
    """Test we can import from network."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "host": "localhost",
        "port": "1234",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "localhost:1234"
    assert result["data"] == {**entry_data, **SERIAL_DATA}


async def test_import_update(hass, dsmr_connection_send_validate_fixture):
    """Test we can import."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=entry_data,
        unique_id="/dev/ttyUSB0",
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.dsmr.async_setup_entry", return_value=True
    ), patch("homeassistant.components.dsmr.async_unload_entry", return_value=True):
        await hass.config_entries.async_setup(entry.entry_id)

    await hass.async_block_till_done()

    new_entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 3,
        "reconnect_interval": 30,
    }

    with patch(
        "homeassistant.components.dsmr.async_setup_entry", return_value=True
    ), patch("homeassistant.components.dsmr.async_unload_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=new_entry_data,
        )

        await hass.async_block_till_done()

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"

    assert entry.data["precision"] == 3


async def test_options_flow(hass):
    """Test options flow."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "2.2",
        "precision": 4,
        "reconnect_interval": 30,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=entry_data,
        unique_id="/dev/ttyUSB0",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "time_between_update": 15,
        },
    )

    with patch(
        "homeassistant.components.dsmr.async_setup_entry", return_value=True
    ), patch("homeassistant.components.dsmr.async_unload_entry", return_value=True):
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        await hass.async_block_till_done()

    assert entry.options == {"time_between_update": 15}


async def test_import_luxembourg(hass, dsmr_connection_send_validate_fixture):
    """Test we can import."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "5L",
        "precision": 4,
        "reconnect_interval": 30,
    }

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "/dev/ttyUSB0"
    assert result["data"] == {**entry_data, **SERIAL_DATA}


async def test_import_sweden(hass, dsmr_connection_send_validate_fixture):
    """Test we can import."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry_data = {
        "port": "/dev/ttyUSB0",
        "dsmr_version": "5S",
        "precision": 4,
        "reconnect_interval": 30,
    }

    with patch("homeassistant.components.dsmr.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=entry_data,
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "/dev/ttyUSB0"
    assert result["data"] == {**entry_data, **SERIAL_DATA_SWEDEN}


def test_get_serial_by_id_no_dir():
    """Test serial by id conversion if there's no /dev/serial/by-id."""
    p1 = patch("os.path.isdir", MagicMock(return_value=False))
    p2 = patch("os.scandir")
    with p1 as is_dir_mock, p2 as scan_mock:
        res = config_flow.get_serial_by_id(sentinel.path)
        assert res is sentinel.path
        assert is_dir_mock.call_count == 1
        assert scan_mock.call_count == 0


def test_get_serial_by_id():
    """Test serial by id conversion."""
    p1 = patch("os.path.isdir", MagicMock(return_value=True))
    p2 = patch("os.scandir")

    def _realpath(path):
        if path is sentinel.matched_link:
            return sentinel.path
        return sentinel.serial_link_path

    p3 = patch("os.path.realpath", side_effect=_realpath)
    with p1 as is_dir_mock, p2 as scan_mock, p3:
        res = config_flow.get_serial_by_id(sentinel.path)
        assert res is sentinel.path
        assert is_dir_mock.call_count == 1
        assert scan_mock.call_count == 1

        entry1 = MagicMock(spec_set=os.DirEntry)
        entry1.is_symlink.return_value = True
        entry1.path = sentinel.some_path

        entry2 = MagicMock(spec_set=os.DirEntry)
        entry2.is_symlink.return_value = False
        entry2.path = sentinel.other_path

        entry3 = MagicMock(spec_set=os.DirEntry)
        entry3.is_symlink.return_value = True
        entry3.path = sentinel.matched_link

        scan_mock.return_value = [entry1, entry2, entry3]
        res = config_flow.get_serial_by_id(sentinel.path)
        assert res is sentinel.matched_link
        assert is_dir_mock.call_count == 2
        assert scan_mock.call_count == 2
