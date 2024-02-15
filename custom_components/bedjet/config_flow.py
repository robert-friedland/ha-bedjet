import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_MAC

from . import DOMAIN

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MAC): str,
    }
)

class BedjetDeviceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="BedJet", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=DEVICE_SCHEMA,
            description_placeholders={
                "mac_helper_text": "Enter the MAC address of your BedJet device (optional)."
            },
            errors=errors,
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Update Bedjet Mac", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=DEVICE_SCHEMA,
            description_placeholders={
                "mac_helper_text": "Enter the MAC address of your BedJet device (optional)."
            },
        )
