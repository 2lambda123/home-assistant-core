"""Describe group states."""

from homeassistant.components.group import GroupIntegrationRegistry
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED
from homeassistant.core import HomeAssistant, callback


@callback
def async_describe_on_off_states(
    hass: HomeAssistant, registry: GroupIntegrationRegistry
) -> None:
    """Describe group on off states."""
    registry.on_off_states({STATE_UNLOCKED}, STATE_LOCKED)
