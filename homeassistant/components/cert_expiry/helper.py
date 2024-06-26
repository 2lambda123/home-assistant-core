"""Helper functions for the Cert Expiry platform."""

from functools import cache
import socket
import ssl

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import TIMEOUT
from .errors import (
    ConnectionRefused,
    ConnectionTimeout,
    ResolveFailed,
    ValidationFailure,
)


@cache
def _get_default_ssl_context():
    """Return the default SSL context."""
    return ssl.create_default_context()


def get_cert(
    host: str,
    port: int,
):
    """Get the certificate for the host and port combination."""
    ctx = _get_default_ssl_context()
    address = (host, port)
    with (
        socket.create_connection(address, timeout=TIMEOUT) as sock,
        ctx.wrap_socket(sock, server_hostname=address[0]) as ssock,
    ):
        cert = ssock.getpeercert()
        return cert


async def get_cert_expiry_timestamp(
    hass: HomeAssistant,
    hostname: str,
    port: int,
):
    """Return the certificate's expiration timestamp."""
    try:
        cert = await hass.async_add_executor_job(get_cert, hostname, port)
    except socket.gaierror as err:
        raise ResolveFailed(f"Cannot resolve hostname: {hostname}") from err
    except TimeoutError as err:
        raise ConnectionTimeout(
            f"Connection timeout with server: {hostname}:{port}"
        ) from err
    except ConnectionRefusedError as err:
        raise ConnectionRefused(
            f"Connection refused by server: {hostname}:{port}"
        ) from err
    except ssl.CertificateError as err:
        raise ValidationFailure(err.verify_message) from err
    except ssl.SSLError as err:
        raise ValidationFailure(err.args[0]) from err

    ts_seconds = ssl.cert_time_to_seconds(cert["notAfter"])
    return dt_util.utc_from_timestamp(ts_seconds)
