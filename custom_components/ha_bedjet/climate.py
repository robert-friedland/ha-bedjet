import datetime
from datetime import timedelta
import logging

import pygatt
from binascii import hexlify
import time
import math
import datetime
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.const import (CONF_NAME, CONF_MAC)
import homeassistant.util.dt as dt_util
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = [
    'pygatt==4.0.5'
]

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    SUPPORT_FAN_MODE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT, 
    HVAC_MODE_COOL,
    HVAC_MODE_DRY
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_FAHRENHEIT
)

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

BEDJET_COMMAND_UUID = '00002004-bed0-0080-aa55-4265644a6574'
BEDJET_SUBSCRIPTION_UUID = '00002000-bed0-0080-aa55-4265644a6574'
MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(seconds=120)

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

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_MAC): cv.string
})

ADAPTER = pygatt.backends.GATTToolBackend()
ADAPTER.start(reset_on_start=False)

def setup_platform(hass, config, add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    mac = config.get(CONF_MAC)

    add_entities(
        [BedJet(name, mac, ADAPTER)]
    )

class BedJet(ClimateEntity):
    def __init__(self, name, mac, adapter):
        self._name = name
        self._mac = mac

        self._current_temperature = None
        self._target_temperature = None
        self._last_seen = None
        self._hvac_mode = None
        self._preset_mode = None

        self._time = None
        self._timestring = None
        self._fan_pct = None

        self._adapter = adapter
        self._device = None

        if not self.connect():
            raise Exception(f'Could not establish connection to {self._name}.')
        
        if not self.subscribe():
            raise Exception(f'Could not subscribe to {self._name}.')

    @property
    def name(self):
        return self._name
    
    @property
    def unique_id(self):
        return "_".join([self._name, "climate"])

    @property
    def should_poll(self):
        return True

    @property
    def temperature_unit(self):
        return TEMP_FAHRENHEIT
    
    @property
    def current_temperature(self):
        return self._current_temperature
    
    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def available(self):
        return True

    @property
    def last_seen(self):
        return self._last_seen

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_DRY]

    @property
    def hvac_mode(self):
        return self._hvac_mode
    
    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE | SUPPORT_FAN_MODE
    
    @property
    def preset_modes(self):
        return ['off','cool','heat','turbo','dry','ext_ht','m1','m2','m3']
        
    @property
    def preset_mode(self):
        return self._preset_mode
        
    @property
    def fan_modes(self):
        return ['FAN_MIN', 'FAN_LOW', 'FAN_MEDIUM', 'FAN_HIGH', 'FAN_MAX']
        
    @property
    def min_temp(self):
        return 66
    
    @property
    def max_temp(self):
        return 109
    
    @property
    def fan_mode(self):
        if self._fan_pct <= 10:
            return 'FAN_MIN'
        if self._fan_pct <= 25:
            return 'FAN_LOW'
        if self._fan_pct <= 50:
            return 'FAN_MEDIUM'
        if self._fan_pct <= 75:
            return 'FAN_HIGH'
        return 'FAN_MAX'

    # connects to the BedJet. BedJet can only be connected to one device at a time, so if you have the remote on or your phone app connected, this will fail
    # it also randomly fails (??) but if you retry enough, it works
    def connect(self):
        max_tries = 10
        for i in range(0, max_tries):
            try:
                self._device = self._adapter.connect(self._mac)
                self._device.resubscribe_all()
                return True
            except pygatt.exceptions.NotConnectedError:
                print(f'Failed to connect to {self._mac} on try {str(i+1)} of {str(max_tries)}.')
        
        return False
    
    # sends a command to the BedJet. sometimes the BedJet gets disconnected, so you have to reconnect before you can issue the command
    def send_command(self, addr, cmd):
        for i in range(0, 10):
            try:
                self._device.char_write(addr, cmd)
                return True
            except pygatt.exceptions.NotificationTimeout:
                print('Trying again')
            except pygatt.exceptions.NotConnectedError:
                self.connect()

        return False

    # subscribes to notifications from the BedJet. again, sometimes fails, so have to implement retries
    def subscribe(self):
        for j in range(0, 5):
            try:
                self._device.subscribe(BEDJET_SUBSCRIPTION_UUID, callback=self.handle_data)
                return True
            except pygatt.exceptions.NotificationTimeout:
                print('Trying again')
            except pygatt.exceptions.NotConnectedError:
                self.connect()

        return False
        
    def unsubscribe(self):
        for j in range(0, 5):
            try:
                self._device.unsubscribe(BEDJET_SUBSCRIPTION_UUID, wait_for_response=True)
                return True
            except pygatt.exceptions.NotificationTimeout:
                print('Trying again')
            except pygatt.exceptions.NotConnectedError:
                self.connect()

        return False

    # parses the notifications from the BedJet
    def handle_data(self, handle, value):
        self._current_temperature = round(((int(value[7]) - 0x26) + 66) - ((int(value[7]) - 0x26) / 9))
        self._target_temperature = round(((int(value[8]) - 0x26) + 66) - ((int(value[8]) - 0x26) / 9))
        self._time = (int(value[4]) * 60 *60) + (int(value[5]) * 60) + int(value[6])
        self._timestring = str(int(value[4])) + ":" + str(int(value[5])) + ":" + str(int(value[6]))
        self._fan_pct = int(value[10]) * 5
        if value[14] == 0x50 and value[13] == 0x14:
            self._hvac_mode = HVAC_MODE_OFF
            self._preset_mode = "off"
        if value[14] == 0x34:
            self._hvac_mode = HVAC_MODE_COOL
            self._preset_mode = "cool"
        if value[14] == 0x56:
            self._hvac_mode = HVAC_MODE_HEAT
            self._preset_mode = "turbo"
        if value[14] == 0x50 and value[13] == 0x2d:
            self._hvac_mode = HVAC_MODE_HEAT
            self._preset_mode = "heat"
        if value[14] == 0x3e:
            self._hvac_mode = HVAC_MODE_DRY
            self._preset_mode = "dry"
        if value[14] == 0x43:
            self._hvac_mode = HVAC_MODE_HEAT
            self._preset_mode = "ext_ht"

        self._last_seen = datetime.datetime.now()

    # sets the BedJet mode. the Climate entity treats hvac and preset modes differently, but BedJet does not, so both hvac and preset sets call this function
    def set_mode(self, mode):
        self.send_command(BEDJET_COMMAND_UUID, [0x01,mode])
        
    # unused in Climate entity but may be useful later
    def press_control(self, control):
        self.send_command(BEDJET_COMMAND_UUID, [0x01,control])
    
    # unused in Climate entity but may be useful later
    def press_preset(self, preset):
        self.send_command(BEDJET_COMMAND_UUID, [0x01,preset])

    # unused in Climate entity but may be useful later    
    def set_time(self, minutes):
        self.send_command(BEDJET_COMMAND_UUID, [0x02, minutes // 60, minutes % 60])

    def set_fan_mode(self, fan_mode):
        if fan_mode == 'FAN_MIN':
            fan_pct = 10
        if fan_mode == 'FAN_LOW':
            fan_pct = 25
        if fan_mode == 'FAN_MEDIUM':
            fan_pct = 50
        if fan_mode == 'FAN_HIGH':
            fan_pct = 75
        if fan_mode == 'FAN_MAX':
            fan_pct = 100
        self.send_command(BEDJET_COMMAND_UUID, [0x07,round(fan_pct/5)-1])

    def set_temperature(self, **kwargs):
        temp = int(kwargs.get(ATTR_TEMPERATURE))
        temp_byte = (int((temp - 60) / 9) + (temp - 66))  + 0x26
        self.send_command(BEDJET_COMMAND_UUID, [0x03,temp_byte])

    def set_hvac_mode(self, hvac_mode):
        self.set_mode(BEDJET_COMMANDS[hvac_mode])
        self.set_time(600)
        
    def set_preset_mode(self, preset_mode):
        self.set_mode(BEDJET_COMMANDS[preset_mode])
    
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.unsubscribe()
        self.subscribe()
