# homeassistant-cz20-badge
Connect cz2020 badge from badge.team to home-assistant as binary sensor and rgb light.

16 buttons and lights are automatically detected by homeassistant using MQTT.
Button numbers are from 0 to 15
[github](https://github.com/JeroenvO/homeassistant-cz20-badge)

## Setup
Make sure to put the correct settings in the app settings menu of https://webusb.hackz.one. 
Set the server ip of the mqtt server of homeassistant (usually the same ip as your homeassistant).
Make sure MQTT and autodiscovery are enabled in your homeassistant config.
Choose any device name for the device (default: cz2020) and optionally change the [discovery prefix](https://www.home-assistant.io/docs/mqtt/discovery/#discovery_prefix).

## Startup sequence
On startup, all keys turn red. The first row turns orange when starting connect to wifi, and to green if wifi connection was successful.
The second row turns orange when connecting to the mqtt server, and to green if connected successful.
If the second doesn't turn green, check the mqtt server address in the settings of https://webusb.hackz.one
The third and fourth row turn orange when starting programming of homeassistant and setting all states to available, and green on success.

## Using
In the homeassistant website, navigate to 'Configuration' and click 'Devices". <device_name> (default: cz2020), should show in the list of devices. 
Click it to view the states of all 16 buttons and their light. Add automations based on button presses. Use the trigger 'Duration' to program long-presses of the buttons.

## Credits

Basic structure based on: https://badge.team/projects/mqtt_button
Light structure based on: https://github.com/mertenats/open-home-automation/tree/master/ha_mqtt_rgb_light