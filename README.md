# Home Assistant BedJet

This project contains a climate entity that provides control of a [BedJet](https://bedjet.com) device.

## Installation (HACS) - Recommended

0. Have [HACS](https://custom-components.github.io/hacs/installation/manual/) installed, this will allow you to easily update
1. Add `https://github.com/robert-friedland/ha-bedjet` as a [custom repository](https://custom-components.github.io/hacs/usage/settings/#add-custom-repositories) as Type: Integration
2. Click install under "HA-BedJet", restart your instance.

## Installation (Manual)

1. Download this repository as a ZIP (green button, top right) and unzip the archive
2. Copy `/custom_components/ha_bedjet` to your `<config_dir>/custom_components/` directory
   - You will need to create the `custom_components` folder if it does not exist
   - On Hassio the final location will be `/config/custom_components/ha_bedjet`
   - On Hassbian the final location will be `/home/homeassistant/.homeassistant/custom_components/ha_bedjet`

## Configuration

Add the following to your `configuration.yaml` file:

```yaml
# Example entry

climate:
  - platform: ha_bedjet
```

Configuration variables:

- **mac** (_Optional_): Bluetooth MAC address of your BedJet, if you want to specify. If not specified, this integration will search for all BedJets within range.

## Screenshot

![screenshot](https://i.imgur.com/Y836CWU.png)
