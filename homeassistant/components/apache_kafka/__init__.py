"""Support for Apache Kafka."""

from datetime import datetime
import json
import sys

import voluptuous as vol

from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    EVENT_STATE_CHANGED,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entityfilter import FILTER_SCHEMA
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ssl as ssl_util

if sys.version_info < (3, 12):
    from aiokafka import AIOKafkaProducer


DOMAIN = "apache_kafka"

CONF_FILTER = "filter"
CONF_TOPIC = "topic"
CONF_SECURITY_PROTOCOL = "security_protocol"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_IP_ADDRESS): cv.string,
                vol.Required(CONF_PORT): cv.port,
                vol.Required(CONF_TOPIC): cv.string,
                vol.Optional(CONF_FILTER, default={}): FILTER_SCHEMA,
                vol.Optional(CONF_SECURITY_PROTOCOL, default="PLAINTEXT"): vol.In(
                    ["PLAINTEXT", "SASL_SSL"]
                ),
                vol.Optional(CONF_USERNAME): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Activate the Apache Kafka integration."""
    if sys.version_info >= (3, 12):
        raise HomeAssistantError(
            "Apache Kafka is not supported on Python 3.12. Please use Python 3.11."
        )
    conf = config[DOMAIN]

    kafka = hass.data[DOMAIN] = KafkaManager(
        hass,
        conf[CONF_IP_ADDRESS],
        conf[CONF_PORT],
        conf[CONF_TOPIC],
        conf[CONF_FILTER],
        conf[CONF_SECURITY_PROTOCOL],
        conf.get(CONF_USERNAME),
        conf.get(CONF_PASSWORD),
    )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, kafka.shutdown)

    await kafka.start()

    return True


class DateTimeJSONEncoder(json.JSONEncoder):
    """Encode python objects.

    Additionally add encoding for datetime objects as isoformat.
    """

    def default(self, o):
        """Implement encoding logic."""
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class KafkaManager:
    """Define a manager to buffer events to Kafka."""

    def __init__(
        self,
        hass,
        ip_address,
        port,
        topic,
        entities_filter,
        security_protocol,
        username,
        password,
    ):
        """Initialize."""
        self._encoder = DateTimeJSONEncoder()
        self._entities_filter = entities_filter
        self._hass = hass
        ssl_context = ssl_util.client_context()
        self._producer = AIOKafkaProducer(
            bootstrap_servers=f"{ip_address}:{port}",
            compression_type="gzip",
            security_protocol=security_protocol,
            ssl_context=ssl_context,
            sasl_mechanism="PLAIN",
            sasl_plain_username=username,
            sasl_plain_password=password,
        )
        self._topic = topic

    def _encode_event(self, event):
        """Translate events into a binary JSON payload."""
        state = event.data.get("new_state")
        if (
            state is None
            or state.state in (STATE_UNKNOWN, "", STATE_UNAVAILABLE)
            or not self._entities_filter(state.entity_id)
        ):
            return

        return json.dumps(obj=state.as_dict(), default=self._encoder.encode).encode(
            "utf-8"
        )

    async def start(self):
        """Start the Kafka manager."""
        self._hass.bus.async_listen(EVENT_STATE_CHANGED, self.write)
        await self._producer.start()

    async def shutdown(self, _):
        """Shut the manager down."""
        await self._producer.stop()

    async def write(self, event):
        """Write a binary payload to Kafka."""
        payload = self._encode_event(event)

        if payload:
            await self._producer.send_and_wait(self._topic, payload)
