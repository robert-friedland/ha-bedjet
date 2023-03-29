DOMAIN = "bedjet"

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )
    return True
