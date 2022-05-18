# Home Assistant BedJet

This project contains a climate entity that provides control of a [BedJet](https://bedjet.com) device.

## Installation (HACS) - Recommended
0. Have [HACS](https://custom-components.github.io/hacs/installation/manual/) installed, this will allow you to easily update
1. Add `https://github.com/robert-friedland/ha-bedjet` as a [custom repository](https://custom-components.github.io/hacs/usage/settings/#add-custom-repositories) as Type: Integration
2. Click install under "HA-BedJet", restart your instance.

## Installation (Manual)
1. Download this repository as a ZIP (green button, top right) and unzip the archive
2. Copy `/custom_components/ha_bedjet` to your `<config_dir>/custom_components/` directory
   * You will need to create the `custom_components` folder if it does not exist
   * On Hassio the final location will be `/config/custom_components/ha_bedjet`
   * On Hassbian the final location will be `/home/homeassistant/.homeassistant/custom_components/ha_bedjet`

## Configuration

Add the following to your `configuration.yaml` file:

```yaml
# Example entry

climate:
  - platform: ha_bedjet
    name: BedJet
    mac: '54:98:23:62:3e:0f'
```

Configuration variables:

- **name** (*Required*): Name of your BedJet
- **mac** (*Required*): Bluetooth MAC address of your BedJet

## Screenshot

![screenshot](https://i.imgur.com/Y836CWU.png)

## Finding BedJet MAC Address

I found mine using [Bluetooth LE Explorer](https://www.microsoft.com/en-us/p/bluetooth-le-explorer/9n0ztkf1qd98?activetab=pivot:overviewtab). The BedJet will be the device named BEDJET_V3.

## Tips

~The BedJet can only maintain one connection at a time; when you install this component, you will not be able to use your remote or the BedJet app to control the device.~ It seems like this isn't strictly true. I've had success using both this integration and the remote at the same time.

## Reporting an Issue

1. Setup your logger to print debug messages for this component using:
```yaml
logger:
  default: info
  logs:
    custom_components.ha_bedjet: debug
```
2. Restart HA
3. Verify you're still having the issue
4. File an issue in this Github Repository containing your HA log (Developer section > Info > Load Full Home Assistant Log)
   * You can paste your log file at pastebin https://pastebin.com/ and submit a link.
   * Please include details about your setup (Pi, NUC, etc, docker?, HASSOS?)
   * The log file can also be found at `/<config_dir>/home-assistant.log`
