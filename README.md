# Home Assistant BedJet

This project contains a climate entity that provides control of a [BedJet](https://bedjet.com) device.

## Installation (HACS) - Recommended

0. Have [HACS](https://custom-components.github.io/hacs/installation/manual/) installed, this will allow you to easily update
1. Add `https://github.com/asheliahut/ha-bedjet` as a [custom repository](https://custom-components.github.io/hacs/usage/settings/#add-custom-repositories) as Type: Integration
2. Click install under "HA-BedJet", restart your instance.

## Installation (Manual)

1. Download this repository as a ZIP (green button, top right) and unzip the archive
2. Copy `/custom_components/bedjet` to your `<config_dir>/custom_components/` directory
   - You will need to create the `custom_components` folder if it does not exist
   - On Hassio the final location will be `/config/custom_components/bedjet`
   - On Hassbian the final location will be `/home/homeassistant/.homeassistant/custom_components/bedjet`

## Configuration

Follow the configuration flow in devices & services

Configuration variables:

- **mac** (_Optional_): Bluetooth MAC address of your BedJet, if you want to specify. If not specified, this integration will search for all BedJets within range.

## Screenshot

![screenshot](https://i.imgur.com/Y836CWU.png)
