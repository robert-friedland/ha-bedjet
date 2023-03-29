from homeassistant.const import CONF_MAC
from .climate import BedjetDeviceEntity, BedjetDevice
from .discover import discover

import logging

DOMAIN = "bedjet"

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, config_entry, async_add_entities):
    mac = config_entry.data.get(CONF_MAC)
    bedjets = await discover(hass)

    # Filter devices based on MAC address, if applicable
    if mac is not None:
        bedjets = [bj for bj in bedjets if bj.mac == mac]

    # Check if the list of discovered devices is empty
    if not bedjets:
        _LOGGER.warning("No BedJet devices were discovered.")
        return

    # Create BedjetDevice instance
    bedjet_device = BedjetDevice(bedjets)

    # Add entities to Home Assistant
    async_add_entities(bedjet_device.entities, True)
