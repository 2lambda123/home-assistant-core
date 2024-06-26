"""Helper to test significant Alarm Control Panel state changes."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback

from . import ATTR_CHANGED_BY, ATTR_CODE_ARM_REQUIRED

SIGNIFICANT_ATTRIBUTES: set[str] = {
    ATTR_CHANGED_BY,
    ATTR_CODE_ARM_REQUIRED,
}


@callback
def async_check_significant_change(
    hass: HomeAssistant,
    old_state: str,
    old_attrs: dict,
    new_state: str,
    new_attrs: dict,
    **kwargs: Any,
) -> bool | None:
    """Test if state significantly changed."""
    if old_state != new_state:
        return True

    old_attrs_s = set(old_attrs.items())
    new_attrs_s = set(new_attrs.items())
    changed_attrs: set[str] = {item[0] for item in old_attrs_s ^ new_attrs_s}

    for attr_name in changed_attrs:
        if attr_name in SIGNIFICANT_ATTRIBUTES:
            return True

    # no significant attribute change detected
    return False
