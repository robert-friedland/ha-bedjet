from typing import TypedDict, Union
from homeassistant.const import (
    TEMP_FAHRENHEIT
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

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.const import (CONF_NAME, CONF_MAC)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import format_mac

BEDJET_COMMAND_UUID = '00002004-bed0-0080-aa55-4265644a6574'
BEDJET_SUBSCRIPTION_UUID = '00002000-bed0-0080-aa55-4265644a6574'
BEDJET_COMMANDS = {
    "off": 0x01,
    "cool": 0x02,
    "heat": 0x03,
    "turbo": 0x04,
    "dry": 0x05,
    "ext_ht": 0x06,
    "fan_up": 0x10,
    "fan_down": 0x11,
    "temp_up": 0x12,
    "temp_down": 0x13,
    "m1": 0x20,
    "m2": 0x21,
    "m3": 0x22
}
BEDJET_FAN_MODES = {
    "FAN_MIN": 10,
    "FAN_LOW": 25,
    "FAN_MEDIUM": 50,
    "FAN_HIGH": 75,
    "FAN_MAX": 100
}

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


class BedJetState(TypedDict):
    current_temperature: int
    target_temperature: int
    hvac_mode: str
    preset_mode: str
    time: str
    timestring: str
    fan_pct: int
    fan_mode: str
    last_seen: datetime
    available: str


class BedJet(ClimateEntity):
    def __init__(self, device):
        self._mac = device.address

        self._state: BedJetState = BedJetState()

        self.client = BleakClient(
            device, disconnected_callback=self.on_disconnect)

        self.is_connected = self.client.is_connected

    def state_attr(self, attr: str) -> Union[int, str, datetime]:
        return self.bedjet_state.get(attr)

    def set_state_attr(self, attr: str, value: Union[int, str, datetime]):
        if self.state_attr(attr) == value:
            return

        self._state[attr] = value

    @property
    def mac(self):
        return self._mac

    @property
    def bedjet_state(self):
        return self._state

    @property
    def state(self):
        return self.hvac_mode

    @property
    def current_temperature(self) -> int:
        return self.state_attr('current_temperature')

    @property
    def target_temperature(self) -> int:
        return self.state_attr('target_temperature')

    @property
    def time(self) -> str:
        return self.state_attr('time')

    @property
    def timestring(self) -> str:
        return self.state_attr('timestring')

    @property
    def fan_pct(self) -> int:
        return self.state_attr('fan_pct')

    @property
    def hvac_mode(self) -> str:
        return self.state_attr('hvac_mode')

    @property
    def preset_mode(self) -> str:
        return self.state_attr('preset_mode')

    @property
    def client(self):
        return self._client

    @property
    def fan_mode(self) -> str:
        return self.state_attr('fan_mode')

    @property
    def last_seen(self) -> datetime:
        return self.state_attr('last_seen')

    @property
    def is_connected(self):
        return self.state_attr('available') == 'online'

    @property
    def name(self):
        return f'bedjet_{format_mac(self.mac)}'

    @property
    def unique_id(self):
        return f'climate_{self.name}'

    @property
    def temperature_unit(self):
        return TEMP_FAHRENHEIT

    @property
    def available(self):
        return self.is_connected

    @property
    def last_seen(self):
        return self.last_seen

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_DRY]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE | SUPPORT_FAN_MODE

    @property
    def preset_modes(self):
        return ['off', 'cool', 'heat', 'turbo', 'dry', 'ext_ht', 'm1', 'm2', 'm3']

    @property
    def fan_modes(self):
        return ['FAN_MIN', 'FAN_LOW', 'FAN_MEDIUM', 'FAN_HIGH', 'FAN_MAX']

    @property
    def min_temp(self):
        return 66

    @property
    def max_temp(self):
        return 109

    @current_temperature.setter
    def current_temperature(self, value: int):
        self.set_state_attr('current_temperature', value)

    @target_temperature.setter
    def target_temperature(self, value: int):
        self.set_state_attr('target_temperature', value)

    @time.setter
    def time(self, value: str):
        self.set_state_attr('time', value)

    @timestring.setter
    def timestring(self, value: str):
        self.set_state_attr('timestring', value)

    @fan_pct.setter
    def fan_pct(self, value: int):
        self.set_state_attr('fan_pct', value)
        self.set_state_attr('fan_mode', self.determine_fan_mode(value))

    def determine_fan_mode(self, fan_pct: int) -> str:
        fan_pct = fan_pct or 0
        for fan_mode, pct in BEDJET_FAN_MODES.items():
            if fan_pct <= pct:
                return fan_mode

    @hvac_mode.setter
    def hvac_mode(self, value: str):
        self.set_state_attr('hvac_mode', value)

    @preset_mode.setter
    def preset_mode(self, value: str):
        self.set_state_attr('preset_mode', value)

    @client.setter
    def client(self, value):
        self._client = value

    @last_seen.setter
    def last_seen(self, value: datetime):
        self.set_state_attr('last_seen', value)

    @is_connected.setter
    def is_connected(self, value: bool):
        self.set_state_attr('available', 'online' if value else 'offline')

    async def connect(self, max_retries=10):
        reconnect_interval = 3
        for i in range(0, max_retries):
            try:
                _LOGGER.info(f'Attempting to connect to {self.mac}.')
                await self.client.connect()
                self.is_connected = self.client.is_connected
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
                break

        if not self.is_connected:
            _LOGGER.error(
                f'Failed to connect to {self.mac} after {max_retries} attempts.')
            raise Exception(
                f'Failed to connect to {self.mac} after {max_retries} attempts.')

    async def connect_and_subscribe(self, max_retries=10):
        await self.connect(max_retries)
        await self.subscribe(max_retries)

    def on_disconnect(self, client):
        self.is_connected = False
        _LOGGER.warning(f'Disconnected from {self.mac}.')
        asyncio.create_task(self.connect_and_subscribe())

    async def disconnect(self):
        self.client.set_disconnected_callback(None)
        await self.client.disconnect()

    def handle_data(self, handle, value):
        def get_current_temperature(value):
            return round(((int(value[7]) - 0x26) + 66) - ((int(value[7]) - 0x26) / 9))

        def get_target_temperature(value):
            return round(((int(value[8]) - 0x26) + 66) - ((int(value[8]) - 0x26) / 9))

        def get_time(value):
            return (int(value[4]) * 60 * 60) + (int(value[5]) * 60) + int(value[6])

        def get_timestring(value):
            return str(int(value[4])) + ":" + str(int(value[5])) + ":" + str(int(value[6]))

        def get_fan_pct(value):
            return int(value[10]) * 5

        def get_preset_mode(value):
            if value[14] == 0x50 and value[13] == 0x14:
                return "off"
            if value[14] == 0x34:
                return "cool"
            if value[14] == 0x56:
                return "turbo"
            if value[14] == 0x50 and value[13] == 0x2d:
                return "heat"
            if value[14] == 0x3e:
                return "dry"
            if value[14] == 0x43:
                return "ext_ht"

        def get_hvac_mode(value):
            PRESET_TO_HVAC = {
                'off': 'off',
                'cool': 'cool',
                'turbo': 'heat',
                'heat': 'heat',
                'dry': 'dry',
                'ext_ht': 'heat'
            }

            return PRESET_TO_HVAC[get_preset_mode(value)]

        self.current_temperature = get_current_temperature(value)
        self.target_temperature = get_target_temperature(value)
        self.time = get_time(value)
        self.timestring = get_timestring(value)
        self.fan_pct = get_fan_pct(value)
        self.hvac_mode = get_hvac_mode(value)
        self.preset_mode = get_preset_mode(value)
        self.last_seen = datetime.now()

        self.schedule_update_ha_state()

    async def subscribe(self, max_retries=10):
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

    async def async_set_fan_mode(self, fan_mode):
        if str(fan_mode).isnumeric():
            fan_pct = int(fan_mode)
        else:
            fan_pct = BEDJET_FAN_MODES.get(fan_mode)

        if not (fan_pct >= 0 and fan_pct <= 100):
            return

        await self.send_command([0x07, round(fan_pct/5)-1])

    async def async_set_temperature(self, temperature):
        temp = round(float(temperature))
        temp_byte = (int((temp - 60) / 9) + (temp - 66)) + 0x26
        await self.send_command([0x03, temp_byte])

    async def async_set_hvac_mode(self, hvac_mode):
        await self.set_mode(BEDJET_COMMANDS.get(hvac_mode))
        await self.set_time(600)

    async def async_set_preset_mode(self, preset_mode):
        await self.set_mode(BEDJET_COMMANDS.get(preset_mode))
