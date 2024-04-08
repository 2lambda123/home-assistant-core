"""Test the Tessie cover platform."""

from unittest.mock import patch

import pytest
from syrupy import SnapshotAssertion

from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    STATE_CLOSED,
    STATE_OPEN,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .common import ERROR_UNKNOWN, TEST_RESPONSE, TEST_RESPONSE_ERROR, setup_platform


@pytest.mark.parametrize(
    ("entity_id", "openfunc", "closefunc"),
    [
        ("cover.test_vent_windows", "vent_windows", "close_windows"),
        ("cover.test_charge_port_door", "open_unlock_charge_port", "close_charge_port"),
        ("cover.test_frunk", "open_front_trunk", False),
        ("cover.test_trunk", "open_close_rear_trunk", "open_close_rear_trunk"),
    ],
)
async def test_covers(
    hass: HomeAssistant,
    entity_id: str,
    openfunc: str,
    closefunc: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Tests that the window cover entity is correct."""

    await setup_platform(hass)

    assert hass.states.get(entity_id) == snapshot(name=entity_id)

    # Test open windows
    if openfunc:
        with patch(
            f"homeassistant.components.tessie.cover.{openfunc}",
            return_value=TEST_RESPONSE,
        ) as mock_open:
            await hass.services.async_call(
                COVER_DOMAIN,
                SERVICE_OPEN_COVER,
                {ATTR_ENTITY_ID: [entity_id]},
                blocking=True,
            )
            mock_open.assert_called_once()
        assert hass.states.get(entity_id).state == STATE_OPEN

    # Test close windows
    if closefunc:
        with patch(
            f"homeassistant.components.tessie.cover.{closefunc}",
            return_value=TEST_RESPONSE,
        ) as mock_close:
            await hass.services.async_call(
                COVER_DOMAIN,
                SERVICE_CLOSE_COVER,
                {ATTR_ENTITY_ID: [entity_id]},
                blocking=True,
            )
            mock_close.assert_called_once()
        assert hass.states.get(entity_id).state == STATE_CLOSED


async def test_errors(hass: HomeAssistant) -> None:
    """Tests errors are handled."""

    await setup_platform(hass)
    entity_id = "cover.test_charge_port_door"

    # Test setting cover open with unknown error
    with (
        patch(
            "homeassistant.components.tessie.cover.open_unlock_charge_port",
            side_effect=ERROR_UNKNOWN,
        ) as mock_set,
        pytest.raises(HomeAssistantError) as error,
    ):
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_set.assert_called_once()
        assert error.from_exception == ERROR_UNKNOWN


async def test_response_error(hass: HomeAssistant) -> None:
    """Tests response errors are handled."""

    await setup_platform(hass)
    entity_id = "cover.test_charge_port_door"

    # Test setting cover open with unknown error
    with (
        patch(
            "homeassistant.components.tessie.cover.open_unlock_charge_port",
            return_value=TEST_RESPONSE_ERROR,
        ) as mock_set,
        pytest.raises(HomeAssistantError) as error,
    ):
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_set.assert_called_once()
        assert str(error) == TEST_RESPONSE_ERROR["reason"]
