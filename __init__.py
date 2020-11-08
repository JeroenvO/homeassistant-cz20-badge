"""
Copyright Jeroen van Oorschot 2020
https://jjvanoorschot.nl
MIT Licence
"""


import touchpads, keypad, display, wifi, audio, time, system, appconfig, machine
from umqtt.simple import MQTTClient
import binascii

# Get the settings from the settings menu
settings = appconfig.get('homeassistant-cz20-badge', {'MQTT_server_ip': "192.168.1.104",
                                                      'MQTT_device_name': "cz2020",
                                                      'MQTT_discovery_prefix': 'homeassistant'})
SERVER_IP = settings['MQTT_server_ip']
DEVICE_NAME = settings['MQTT_device_name'].strip('/')
PREFIX = settings['MQTT_discovery_prefix'].strip('/')
UUID = binascii.hexlify(machine.unique_id()).decode()
DEVICE_CONFIG = '{\
"identifiers": "' + UUID + '",\
"name": "' + DEVICE_NAME + '",\
"sw_version": "cz2020-badge.team v0.1",\
"model": "CZ2020",\
"manufacturer": "badge.team"\
}'
ORANGE = 0xFF5500
RED = 0xff0000
GREEN = 0x00ff00
COLORS = [[255, 255, 255]] * 16  # save color, brightness for each button.
BRIGHTNESS = [255] * 16  # save brightness for each button.
STATE = [False] * 16  # save state for each button.

# Clear the screen
display.drawFill(0xff0000)
display.flush()


def set_color(key_index, on=True):
    x, y = key_index % 4, int(key_index / 4)
    if on:
        cs = [int(c * BRIGHTNESS[key_index] / 255) for c in COLORS[key_index]]
        display.drawPixel(x, y, (cs[0] << 16) + (cs[1] << 8) + cs[2])
    else:
        display.drawPixel(x, y, 0)
    display.flush()


# Key press handler
def on_key(key_index, pressed):
    global c
    # print('key event', key_index)
    topic = PREFIX + '/binary_sensor/' + DEVICE_NAME + '/' + str(key_index) + '/state'
    if pressed:
        x, y = key_index % 4, int(key_index / 4)
        c.publish(topic, "ON")
        display.drawPixel(x, y, RED)
        display.flush()
    else:
        c.publish(topic, "OFF")
        set_color(key_index)


# When the home key is pressed, disconnect everything and return to home
def on_home(is_pressed):
    global c
    # print('home button: ' + str(is_pressed))
    if is_pressed == 512:
        display.drawFill(RED)
        display.flush()
        for key_index in range(16):  # each button
            topic = PREFIX + '/binary_sensor/' + DEVICE_NAME + '/' + str(key_index) + '/'
            c.publish(topic + "status", "offline")
            topic = PREFIX + '/light/' + DEVICE_NAME + '/' + str(key_index) + '/'
            c.publish(topic + "status", "offline")
        c.disconnect()
        system.launcher()


# MQTT subscribe handler
def sub_cb(topic, msg):
    global c
    # print((topic, msg))
    # Split the topic into a list. 0=prefix, 1=integration, 2=device, 3=key index
    # integration = int(topic.decode('utf-8').split('/')[1])  # this will always be "light"
    topic = topic.decode('utf-8').split('/')
    key_index = int(topic[3])
    command = topic[4]
    topic_u = PREFIX + '/light/' + DEVICE_NAME + '/' + str(key_index) + '/'
    msg = msg.decode('utf-8')
    if command == 'switch':
        if msg == 'ON':
            STATE[key_index] = True
            set_color(key_index)
            c.publish(topic_u + 'state', 'ON')
        elif msg == 'OFF':
            STATE[key_index] = False
            set_color(key_index, False)
            c.publish(topic_u + 'state', 'ON')
        else:
            print('invalid')
    elif command == 'rgb' and topic[5] == 'set':
        COLORS[key_index] = [int(c) for c in msg.split(',')]
        set_color(key_index)
        c.publish(topic_u + 'rgb/state', msg)
    elif command == 'brightness' and topic[5] == 'set':
        BRIGHTNESS[key_index] = int(msg)
        set_color(key_index)
        c.publish(topic_u + 'brightness/state', msg)


# start main:
display.flush()
# Connect to Wi-Fi
if not wifi.status():
    wifi.connect()
    display.drawLine(0, 0, 3, 0, ORANGE)
    display.flush()
    wifi.wait()
    if not wifi.status():
        display.drawLine(0, 0, 3, 0, RED)
        display.flush()
        time.sleep(1)
        system.launcher()
display.drawLine(0, 0, 3, 0, 0x00ff00)  # wifi success
display.flush()

# Setup MQTT and connect to it
display.drawLine(0, 1, 3, 1, ORANGE)
display.flush()
c = MQTTClient("umqtt_client", SERVER_IP)
c.set_callback(sub_cb)
# Set a last-will
for key_index in range(16):  # each button
    topic = PREFIX + '/binary_sensor/' + DEVICE_NAME + '/' + str(key_index) + '/'
    c.set_last_will(topic + "status", "offline", retain=True)
    topic = PREFIX + '/light/' + DEVICE_NAME + '/' + str(key_index) + '/'
    c.set_last_will(topic + "status", "offline")

# Connect to MQTT server, fail if not possible and return.
if c.connect():
    print("error connecting")
    display.drawLine(0, 1, 3, 1, RED)
    display.flush()
    time.sleep(1)
    system.launcher()

display.drawLine(0, 1, 3, 1, 0x00ff00)  # mqtt success part 1
display.drawLine(0, 2, 3, 2, ORANGE)  # mqtt start part 2
display.flush()

for key_index in range(16):  # each button
    topic = PREFIX + '/binary_sensor/' + DEVICE_NAME + '/' + str(key_index) + '/'
    message = '{' + '"name": "btn-{key_index:02d}", "state_topic":"{topic}state", "avty_t":"{topic}status", "unique_id":"{UUID}-btn{key_index}", "device":{DEVICE_CONFIG}'.format(
        key_index=key_index, topic=topic, UUID=UUID, DEVICE_CONFIG=DEVICE_CONFIG) + '}'
    c.publish(topic + "config", message)
    c.publish(topic + "status", "online")
    topic = PREFIX + '/light/' + DEVICE_NAME + '/' + str(key_index) + '/'
    message = '{' + \
              '"name": "btn-{key_index:02d}-light","state_topic":"{topic}state","avty_t":"{topic}status","command_topic":"{topic}switch", "brightness_state_topic":"{topic}brightness/state","brightness_command_topic":"{topic}brightness/set","rgb_state_topic":"{topic}rgb/state","rgb_command_topic":"{topic}rgb/set", "unique_id":"{UUID}-btn{key_index}-light", "device":{DEVICE_CONFIG}, "retain":true'. \
                  format(key_index=key_index, topic=topic, UUID=UUID, DEVICE_CONFIG=DEVICE_CONFIG) + '}'
    c.publish(topic + "config", message)
    c.publish(topic + "status", "online")

display.drawLine(0, 2, 3, 2, 0x00ff00)  # mqtt finish part 2
display.drawLine(0, 3, 3, 3, ORANGE)  # mqtt part 3
display.flush()

topic = PREFIX + '/light/' + DEVICE_NAME + '/'
c.subscribe(topic + "#")

display.drawLine(0, 3, 3, 3, GREEN)  # mqtt finish part 2
display.flush()

# Configure the key press handler
keypad.add_handler(on_key)
touchpads.on(touchpads.HOME, on_home)

try:
    while 1:
        c.wait_msg()
finally:
    c.disconnect()
