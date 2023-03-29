import logging
from homeassistant.components import bluetooth

_LOGGER = logging.getLogger(__name__)


async def discover(cls, hass):
    service_infos = await bluetooth.async_discovered_service_info(
        hass, connectable=True)

    bedjet_devices = [
        service_info.device for service_info in service_infos if service_info.name == 'BEDJET_V3']

    _LOGGER.info(
        f'Found {len(bedjet_devices)} BedJet{"" if len(bedjet_devices) == 1 else "s"}: {", ".join([d.address for d in bedjet_devices])}.')

    bedjets = [cls(device) for device in bedjet_devices]

    return bedjets