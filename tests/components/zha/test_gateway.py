"""Test ZHA Gateway."""

import asyncio
from unittest.mock import patch

import pytest
import zigpy.profiles.zha as zha
import zigpy.zcl.clusters.general as general
import zigpy.zcl.clusters.lighting as lighting

from homeassistant.components.zha.core.gateway import ZHAGateway
from homeassistant.components.zha.core.group import GroupMember
from homeassistant.components.zha.core.helpers import get_zha_gateway
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .common import async_find_group_entity_id
from .conftest import SIG_EP_INPUT, SIG_EP_OUTPUT, SIG_EP_PROFILE, SIG_EP_TYPE

from tests.common import MockConfigEntry

IEEE_GROUPABLE_DEVICE = "01:2d:6f:00:0a:90:69:e8"
IEEE_GROUPABLE_DEVICE2 = "02:2d:6f:00:0a:90:69:e8"


@pytest.fixture
def zigpy_dev_basic(zigpy_device_mock):
    """Zigpy device with just a basic cluster."""
    return zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [general.Basic.cluster_id],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        }
    )


@pytest.fixture(autouse=True)
def required_platform_only():
    """Only set up the required and required base platforms to speed up tests."""
    with patch(
        "homeassistant.components.zha.PLATFORMS",
        (
            Platform.SENSOR,
            Platform.LIGHT,
            Platform.DEVICE_TRACKER,
            Platform.NUMBER,
            Platform.SELECT,
        ),
    ):
        yield


@pytest.fixture
async def zha_dev_basic(hass, zha_device_restored, zigpy_dev_basic):
    """ZHA device with just a basic cluster."""

    zha_device = await zha_device_restored(zigpy_dev_basic)
    return zha_device


@pytest.fixture
async def coordinator(hass, zigpy_device_mock, zha_device_joined):
    """Test ZHA light platform."""

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        },
        ieee="00:15:8d:00:02:32:4f:32",
        nwk=0x0000,
        node_descriptor=b"\xf8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
    )
    zha_device = await zha_device_joined(zigpy_device)
    zha_device.available = True
    return zha_device


@pytest.fixture
async def device_light_1(hass, zigpy_device_mock, zha_device_joined):
    """Test ZHA light platform."""

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [
                    general.OnOff.cluster_id,
                    general.LevelControl.cluster_id,
                    lighting.Color.cluster_id,
                    general.Groups.cluster_id,
                ],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        },
        ieee=IEEE_GROUPABLE_DEVICE,
    )
    zha_device = await zha_device_joined(zigpy_device)
    zha_device.available = True
    return zha_device


@pytest.fixture
async def device_light_2(hass, zigpy_device_mock, zha_device_joined):
    """Test ZHA light platform."""

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [
                    general.OnOff.cluster_id,
                    general.LevelControl.cluster_id,
                    lighting.Color.cluster_id,
                    general.Groups.cluster_id,
                ],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        },
        ieee=IEEE_GROUPABLE_DEVICE2,
    )
    zha_device = await zha_device_joined(zigpy_device)
    zha_device.available = True
    return zha_device


async def test_device_left(hass: HomeAssistant, zigpy_dev_basic, zha_dev_basic) -> None:
    """Device leaving the network should become unavailable."""

    assert zha_dev_basic.available is True

    get_zha_gateway(hass).device_left(zigpy_dev_basic)
    await hass.async_block_till_done()
    assert zha_dev_basic.available is False


async def test_gateway_group_methods(
    hass: HomeAssistant, device_light_1, device_light_2, coordinator
) -> None:
    """Test creating a group with 2 members."""
    zha_gateway = get_zha_gateway(hass)
    assert zha_gateway is not None
    zha_gateway.coordinator_zha_device = coordinator
    coordinator._zha_gateway = zha_gateway
    device_light_1._zha_gateway = zha_gateway
    device_light_2._zha_gateway = zha_gateway
    member_ieee_addresses = [device_light_1.ieee, device_light_2.ieee]
    members = [GroupMember(device_light_1.ieee, 1), GroupMember(device_light_2.ieee, 1)]

    # test creating a group with 2 members
    zha_group = await zha_gateway.async_create_zigpy_group("Test Group", members)
    await hass.async_block_till_done()

    assert zha_group is not None
    assert len(zha_group.members) == 2
    for member in zha_group.members:
        assert member.device.ieee in member_ieee_addresses

    entity_id = async_find_group_entity_id(hass, Platform.LIGHT, zha_group)
    assert hass.states.get(entity_id) is not None

    # test get group by name
    assert zha_group == zha_gateway.async_get_group_by_name(zha_group.name)

    # test removing a group
    await zha_gateway.async_remove_zigpy_group(zha_group.group_id)
    await hass.async_block_till_done()

    # we shouldn't have the group anymore
    assert zha_gateway.async_get_group_by_name(zha_group.name) is None

    # the group entity should be cleaned up
    assert entity_id not in hass.states.async_entity_ids(Platform.LIGHT)

    # test creating a group with 1 member
    zha_group = await zha_gateway.async_create_zigpy_group(
        "Test Group", [GroupMember(device_light_1.ieee, 1)]
    )
    await hass.async_block_till_done()

    assert zha_group is not None
    assert len(zha_group.members) == 1
    for member in zha_group.members:
        assert member.device.ieee in [device_light_1.ieee]

    # the group entity should not have been cleaned up
    assert entity_id not in hass.states.async_entity_ids(Platform.LIGHT)

    with patch("zigpy.zcl.Cluster.request", side_effect=asyncio.TimeoutError):
        await zha_group.members[0].async_remove_from_group()
        assert len(zha_group.members) == 1
        for member in zha_group.members:
            assert member.device.ieee in [device_light_1.ieee]


async def test_gateway_create_group_with_id(
    hass: HomeAssistant, device_light_1, coordinator
) -> None:
    """Test creating a group with a specific ID."""
    zha_gateway = get_zha_gateway(hass)
    assert zha_gateway is not None
    zha_gateway.coordinator_zha_device = coordinator
    coordinator._zha_gateway = zha_gateway
    device_light_1._zha_gateway = zha_gateway

    zha_group = await zha_gateway.async_create_zigpy_group(
        "Test Group", [GroupMember(device_light_1.ieee, 1)], group_id=0x1234
    )
    await hass.async_block_till_done()

    assert len(zha_group.members) == 1
    assert zha_group.members[0].device is device_light_1
    assert zha_group.group_id == 0x1234


@pytest.mark.parametrize(
    ("device_path", "config_override", "expected_channel"),
    [
        ("/dev/ttyUSB0", {}, None),
        ("socket://192.168.1.123:9999", {}, None),
        ("socket://192.168.1.123:9999", {"network": {"channel": 20}}, 20),
        ("socket://core-silabs-multiprotocol:9999", {}, 15),
        ("socket://core-silabs-multiprotocol:9999", {"network": {"channel": 20}}, 20),
    ],
)
async def test_gateway_force_multi_pan_channel(
    device_path: str,
    config_override: dict,
    expected_channel: int | None,
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Test ZHA disabling the UART thread when connecting to a TCP coordinator."""
    config_entry.data = dict(config_entry.data)
    config_entry.data["device"]["path"] = device_path
    config_entry.add_to_hass(hass)

    zha_gateway = ZHAGateway(hass, {"zigpy_config": config_override}, config_entry)

    _, config = zha_gateway.get_application_controller_data()
    assert config["network"]["channel"] == expected_channel
