"""The filesize component."""

from __future__ import annotations

import pathlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FILE_PATH
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import PLATFORMS
from .coordinator import FileSizeCoordinator


def _get_full_path(hass: HomeAssistant, path: str) -> str:
    """Check if path is valid, allowed and return full path."""
    get_path = pathlib.Path(path)
    if not get_path.exists() or not get_path.is_file():
        raise ConfigEntryNotReady(f"Can not access file {path}")

    if not hass.config.is_allowed_path(path):
        raise ConfigEntryNotReady(f"Filepath {path} is not valid or allowed")

    return str(get_path.absolute())


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    full_path = await hass.async_add_executor_job(
        _get_full_path, hass, entry.data[CONF_FILE_PATH]
    )
    coordinator = FileSizeCoordinator(hass, full_path)
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
