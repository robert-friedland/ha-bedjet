from enum import Enum
from homeassistant.components.climate.const import HVACMode

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


class PresetMode(Enum):
    OFF = HVACMode.off.value
    COOL = HVACMode.cool.value
    HEAT = HVACMode.heat.value
    DRY = HVACMode.dry.value
    TURBO = 'turbo'
    EXT_HT = 'ext_ht'

    def to_hvac(self) -> HVACMode:
        map = {
            PresetMode.OFF: HVACMode.OFF,
            PresetMode.COOL: HVACMode.COOL,
            PresetMode.HEAT: HVACMode.HEAT,
            PresetMode.DRY: HVACMode.DRY,
            PresetMode.TURBO: HVACMode.HEAT,
            PresetMode.EXT_HT: HVACMode.HEAT
        }

        return map.get(self)

    def command(self):
        return BEDJET_COMMANDS.get(self.value)
