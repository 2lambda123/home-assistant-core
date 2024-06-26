"""Intents for the humidifier integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import ATTR_ENTITY_ID, ATTR_MODE, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
import homeassistant.helpers.config_validation as cv

from . import (
    ATTR_AVAILABLE_MODES,
    ATTR_HUMIDITY,
    DOMAIN,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_MODE,
    SERVICE_TURN_ON,
    HumidifierEntityFeature,
)

INTENT_HUMIDITY = "HassHumidifierSetpoint"
INTENT_MODE = "HassHumidifierMode"


async def async_setup_intents(hass: HomeAssistant) -> None:
    """Set up the humidifier intents."""
    intent.async_register(hass, HumidityHandler())
    intent.async_register(hass, SetModeHandler())


class HumidityHandler(intent.IntentHandler):
    """Handle set humidity intents."""

    intent_type = INTENT_HUMIDITY
    slot_schema = {
        vol.Required("name"): cv.string,
        vol.Required("humidity"): vol.All(vol.Coerce(int), vol.Range(0, 100)),
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the hass intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        states = list(
            intent.async_match_states(
                hass,
                name=slots["name"]["value"],
                states=hass.states.async_all(DOMAIN),
            )
        )

        if not states:
            raise intent.IntentHandleError("No entities matched")

        state = states[0]
        service_data = {ATTR_ENTITY_ID: state.entity_id}

        humidity = slots["humidity"]["value"]

        if state.state == STATE_OFF:
            await hass.services.async_call(
                DOMAIN, SERVICE_TURN_ON, service_data, context=intent_obj.context
            )
            speech = f"Turned {state.name} on and set humidity to {humidity}%"
        else:
            speech = f"The {state.name} is set to {humidity}%"

        service_data[ATTR_HUMIDITY] = humidity
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_HUMIDITY,
            service_data,
            context=intent_obj.context,
            blocking=True,
        )

        response = intent_obj.create_response()

        response.async_set_speech(speech)
        return response


class SetModeHandler(intent.IntentHandler):
    """Handle set humidity intents."""

    intent_type = INTENT_MODE
    slot_schema = {
        vol.Required("name"): cv.string,
        vol.Required("mode"): cv.string,
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the hass intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        states = list(
            intent.async_match_states(
                hass,
                name=slots["name"]["value"],
                states=hass.states.async_all(DOMAIN),
            )
        )

        if not states:
            raise intent.IntentHandleError("No entities matched")

        state = states[0]
        service_data = {ATTR_ENTITY_ID: state.entity_id}

        intent.async_test_feature(state, HumidifierEntityFeature.MODES, "modes")
        mode = slots["mode"]["value"]

        if mode not in state.attributes.get(ATTR_AVAILABLE_MODES, []):
            raise intent.IntentHandleError(
                f"Entity {state.name} does not support {mode} mode"
            )

        if state.state == STATE_OFF:
            await hass.services.async_call(
                DOMAIN,
                SERVICE_TURN_ON,
                service_data,
                context=intent_obj.context,
                blocking=True,
            )
            speech = f"Turned {state.name} on and set {mode} mode"
        else:
            speech = f"The mode for {state.name} is set to {mode}"

        service_data[ATTR_MODE] = mode
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_MODE,
            service_data,
            context=intent_obj.context,
            blocking=True,
        )

        response = intent_obj.create_response()

        response.async_set_speech(speech)
        return response
