"""Describe bthome logbook events."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import async_get
from homeassistant.helpers.typing import EventType

from .const import BTHOME_BLE_EVENT, DOMAIN, BTHomeBleEvent


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[
        [str, str, Callable[[EventType[BTHomeBleEvent]], dict[str, str]]], None
    ],
) -> None:
    """Describe logbook events."""
    dr = async_get(hass)

    @callback
    def async_describe_bthome_event(event: EventType[BTHomeBleEvent]) -> dict[str, str]:
        """Describe bthome logbook event."""
        data = event.data
        device = dr.async_get(data["device_id"])
        name = device and device.name or f"BTHome {data['address']}"
        if properties := data["event_properties"]:
            message = f"{data['event_class']} {data['event_type']}: {properties}"
        else:
            message = f"{data['event_class']} {data['event_type']}"
        return {
            LOGBOOK_ENTRY_NAME: name,
            LOGBOOK_ENTRY_MESSAGE: message,
        }

    async_describe_event(DOMAIN, BTHOME_BLE_EVENT, async_describe_bthome_event)
