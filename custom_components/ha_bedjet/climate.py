from homeassistant.const import (
    TEMP_FAHRENHEIT,
    ATTR_TEMPERATURE
)
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    SUPPORT_FAN_MODE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY
)
from datetime import datetime
import logging
from homeassistant.components import bluetooth
import asyncio
import voluptuous as vol
from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.const import (CONF_NAME, CONF_MAC)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import format_mac

from enum import Enum

from .const import (BEDJET_COMMAND_UUID, BEDJET_COMMANDS,
                    BEDJET_SUBSCRIPTION_UUID)


_LOGGER = logging.getLogger(__name__)

try:
    from homeassistant.components.climate import (
        ClimateEntity,
        PLATFORM_SCHEMA,
    )
except ImportError:
    from homeassistant.components.climate import (
        ClimateDevice as ClimateEntity,
        PLATFORM_SCHEMA,
    )


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=''): cv.string,
    vol.Optional(CONF_MAC, default=''): cv.string,
})


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    mac = config.get(CONF_MAC).upper()

    if config.get(CONF_NAME) != '':
        _LOGGER.warn(
            f'{CONF_NAME} is a deprecated option and will be ignored.')

    if not mac or mac == '':
        _LOGGER.info('Setting up all discoverable BedJets.')
        service_infos = bluetooth.async_discovered_service_info(
            hass, connectable=True)

        bedjet_devices = [
            service_info.device for service_info in service_infos if service_info.name == 'BEDJET_V3']

        _LOGGER.info(
            f'Found {len(bedjet_devices)} BedJet{"" if len(bedjet_devices) == 1 else "s"}: {", ".join([d.address for d in bedjet_devices])}.')

        bedjets = [BedJet(device) for device in bedjet_devices]

    else:
        _LOGGER.info(f'Setting up BedJet with mac address {mac}.')
        device = bluetooth.async_ble_device_from_address(
            hass, mac, connectable=True)
        bedjets = [BedJet(device)]

    for bedjet in bedjets:
        asyncio.create_task(bedjet.connect_and_subscribe())

    add_entities(bedjets)


class FanMode(Enum):
    FAN_MIN = 10
    FAN_LOW = 25
    FAN_MEDIUM = 50
    FAN_HIGH = 75
    FAN_MAX = 100

    @staticmethod
    def get_fan_mode(fan_pct: int | None):
        if not fan_pct:
            return None

        for fan_mode in FanMode:
            if fan_pct <= fan_mode.value:
                return fan_mode

        return None


class HVACMode(Enum):
    off = HVAC_MODE_OFF
    cool = HVAC_MODE_COOL
    heat = HVAC_MODE_HEAT
    dry = HVAC_MODE_DRY

    def command(self):
        return BEDJET_COMMANDS.get(self.value)


class PresetMode(Enum):
    off = HVACMode.off.value
    cool = HVACMode.cool.value
    heat = HVACMode.heat.value
    dry = HVACMode.dry.value
    turbo = 'turbo'
    ext_ht = 'ext_ht'

    def to_hvac(self) -> HVACMode:
        map = {
            PresetMode.off: HVACMode.off,
            PresetMode.cool: HVACMode.cool,
            PresetMode.heat: HVACMode.heat,
            PresetMode.dry: HVACMode.dry,
            PresetMode.turbo: HVACMode.heat,
            PresetMode.ext_ht: HVACMode.heat
        }

        return map.get(self)

    def command(self):
        return BEDJET_COMMANDS.get(self.value)


class BedJet(ClimateEntity):
    def __init__(self, device: BLEDevice):
        self._mac: str = device.address
        self._client: BleakClient = BleakClient(
            device, disconnected_callback=self.on_disconnect)
        self._current_temperature: int | None = None
        self._target_temperature: int | None = None
        self._hvac_mode: HVACMode | None = None
        self._preset_mode: PresetMode | None = None
        self._time: str | None = None
        self._timestring: str | None = None
        self._fan_pct: int | None = None
        self._last_seen: datetime | None = None

    @property
    def mac(self) -> str:
        return self._mac

    @property
    def state(self) -> str | None:
        return self.hvac_mode

    @property
    def current_temperature(self) -> int | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> int | None:
        return self._target_temperature

    @property
    def time(self) -> str | None:
        return self._time

    @property
    def timestring(self) -> str | None:
        return self._timestring

    @property
    def fan_pct(self) -> int | None:
        return self._fan_pct

    @property
    def hvac_mode(self) -> str | None:
        return self._hvac_mode.value if self._hvac_mode else None

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode.value if self._preset_mode else None

    @property
    def client(self) -> BleakClient:
        return self._client

    @property
    def fan_mode(self) -> str | None:
        return FanMode.get_fan_mode(self.fan_pct).name if self.fan_pct else None

    @property
    def last_seen(self) -> datetime:
        return self._last_seen

    @property
    def is_connected(self) -> bool:
        return self.client.is_connected

    @property
    def available(self) -> bool:
        return self.client.is_connected

    @property
    def name(self) -> str:
        return f'bedjet_{format_mac(self.mac)}'

    @property
    def unique_id(self) -> str:
        return f'climate_{self.name}'

    @property
    def temperature_unit(self) -> str:
        return TEMP_FAHRENHEIT

    @property
    def hvac_modes(self) -> list[str]:
        return [mode.value for mode in HVACMode]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE | SUPPORT_FAN_MODE

    @property
    def preset_modes(self) -> list[str]:
        return [mode.value for mode in PresetMode]

    @property
    def fan_modes(self) -> list[str]:
        return [mode.name for mode in FanMode]

    @property
    def min_temp(self) -> int:
        return 66

    @property
    def max_temp(self) -> int:
        return 109

    @current_temperature.setter
    def current_temperature(self, value: int):
        self._current_temperature = value

    @target_temperature.setter
    def target_temperature(self, value: int):
        self._target_temperature = value

    @time.setter
    def time(self, value: str):
        self._time = value

    @timestring.setter
    def timestring(self, value: str):
        self._timestring = value

    @fan_pct.setter
    def fan_pct(self, value: int):
        self._fan_pct = value

    @hvac_mode.setter
    def hvac_mode(self, value: HVACMode):
        self._hvac_mode = value

    @preset_mode.setter
    def preset_mode(self, value: PresetMode):
        self._preset_mode = value

    @client.setter
    def client(self, value: BleakClient):
        self._client = value

    @last_seen.setter
    def last_seen(self, value: datetime):
        self._last_seen = value

    async def connect(self, max_retries=10):
        reconnect_interval = 3
        for i in range(0, max_retries):
            try:
                _LOGGER.info(f'Attempting to connect to {self.mac}.')
                await self.client.connect()
            except Exception as error:
                backoff_seconds = (i+1) * reconnect_interval
                _LOGGER.error(
                    f'Error "{error}". Retrying in {backoff_seconds} seconds.')

                try:
                    _LOGGER.info(f'Attempting to disconnect from {self.mac}.')
                    await self.client.disconnect()
                except BleakError as error:
                    _LOGGER.error(f'Error "{error}".')
                await asyncio.sleep(backoff_seconds)

            if self.is_connected:
                _LOGGER.info(f'Connected to {self.mac}.')
                self.client.set_disconnected_callback(self.on_disconnect)
                break

        if not self.is_connected:
            _LOGGER.error(
                f'Failed to connect to {self.mac} after {max_retries} attempts.')
            raise Exception(
                f'Failed to connect to {self.mac} after {max_retries} attempts.')

    async def connect_and_subscribe(self, max_retries: int = 10):
        await self.connect(max_retries)
        await self.subscribe(max_retries)

    def on_disconnect(self, client: BleakClient):
        _LOGGER.warning(f'Disconnected from {self.mac}.')
        self.client.set_disconnected_callback(None)
        self.schedule_update_ha_state()
        asyncio.create_task(self.connect_and_subscribe())

    async def disconnect(self):
        self.client.set_disconnected_callback(None)
        await self.client.disconnect()

    def handle_data(self, handle, value):
        def get_current_temperature(value) -> int:
            return round(((int(value[7]) - 0x26) + 66) - ((int(value[7]) - 0x26) / 9))

        def get_target_temperature(value) -> int:
            return round(((int(value[8]) - 0x26) + 66) - ((int(value[8]) - 0x26) / 9))

        def get_time(value) -> int:
            return (int(value[4]) * 60 * 60) + (int(value[5]) * 60) + int(value[6])

        def get_timestring(value) -> str:
            return str(int(value[4])) + ":" + str(int(value[5])) + ":" + str(int(value[6]))

        def get_fan_pct(value) -> int:
            return int(value[10]) * 5

        def get_preset_mode(value) -> PresetMode:
            if value[14] == 0x50 and value[13] == 0x14:
                return PresetMode.off
            if value[14] == 0x34:
                return PresetMode.cool
            if value[14] == 0x56:
                return PresetMode.turbo
            if value[14] == 0x50 and value[13] == 0x2d:
                return PresetMode.heat
            if value[14] == 0x3e:
                return PresetMode.heat
            if value[14] == 0x43:
                return PresetMode.ext_ht

        def get_hvac_mode(value) -> HVACMode:
            return get_preset_mode(value).to_hvac()

        self.current_temperature = get_current_temperature(value)
        self.target_temperature = get_target_temperature(value)
        self.time = get_time(value)
        self.timestring = get_timestring(value)
        self.fan_pct = get_fan_pct(value)
        self.hvac_mode = get_hvac_mode(value)
        self.preset_mode = get_preset_mode(value)
        self.last_seen = datetime.now()

        self.schedule_update_ha_state()

    async def subscribe(self, max_retries: int = 10):
        reconnect_interval = 3
        is_subscribed = False

        if not self.client.is_connected:
            await self.connect()

        for i in range(0, max_retries):
            try:
                _LOGGER.info(
                    f'Attempting to subscribe to notifications from {self.mac} on {BEDJET_SUBSCRIPTION_UUID}.')
                await self.client.start_notify(
                    BEDJET_SUBSCRIPTION_UUID, callback=self.handle_data)
                is_subscribed = True
                _LOGGER.info(
                    f'Subscribed to {self.mac} on {BEDJET_SUBSCRIPTION_UUID}.')
                break
            except Exception as error:
                backoff_seconds = (i+1) * reconnect_interval
                _LOGGER.error(
                    f'Error "{error}". Retrying in {backoff_seconds} seconds.')

                await asyncio.sleep(backoff_seconds)

        if not is_subscribed:
            _LOGGER.error(
                f'Failed to subscribe to {self.mac} on {BEDJET_SUBSCRIPTION_UUID} after {max_retries} attempts.')
            raise Exception(
                f'Failed to subscribe to {self.mac} on {BEDJET_SUBSCRIPTION_UUID} after {max_retries} attempts.')

    async def send_command(self, command):
        if self.is_connected:
            return await self._client.write_gatt_char(BEDJET_COMMAND_UUID, command)

    async def set_mode(self, mode):
        return await self.send_command([0x01, mode])

    async def set_time(self, minutes):
        return await self.send_command([0x02, minutes // 60, minutes % 60])

    async def async_set_fan_mode(self, fan_mode: FanMode | int | float):
        if str(fan_mode).isnumeric():
            fan_pct = int(fan_mode)
        else:
            fan_pct = FanMode[fan_mode].value

        if not (fan_pct >= 0 and fan_pct <= 100):
            return

        await self.send_command([0x07, round(fan_pct/5)-1])

    async def async_set_temperature(self, **kwargs):
        temperature = int(kwargs.get(ATTR_TEMPERATURE))
        temp = round(float(temperature))
        temp_byte = (int((temp - 60) / 9) + (temp - 66)) + 0x26
        await self.send_command([0x03, temp_byte])

    async def async_set_hvac_mode(self, hvac_mode: str):
        await self.set_mode(HVACMode(hvac_mode).command())
        await self.set_time(600)

    async def async_set_preset_mode(self, preset_mode: str):
        await self.set_mode(PresetMode(preset_mode).command())
