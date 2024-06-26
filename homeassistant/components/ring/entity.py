"""Base class for Ring entity."""

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import ATTRIBUTION, DOMAIN, RING_DEVICES_COORDINATOR


class RingEntityMixin(Entity):
    """Base implementation for Ring device."""

    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, config_entry_id, device):
        """Initialize a sensor for Ring device."""
        super().__init__()
        self._config_entry_id = config_entry_id
        self._device = device
        self._attr_extra_state_attributes = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            manufacturer="Ring",
            model=device.model,
            name=device.name,
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.ring_objects[RING_DEVICES_COORDINATOR].async_add_listener(
            self._update_callback
        )

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect callbacks."""
        self.ring_objects[RING_DEVICES_COORDINATOR].async_remove_listener(
            self._update_callback
        )

    @callback
    def _update_callback(self) -> None:
        """Call update method."""
        self.async_write_ha_state()

    @property
    def ring_objects(self):
        """Return the Ring API objects."""
        return self.hass.data[DOMAIN][self._config_entry_id]
