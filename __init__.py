"""
Homeassistant CZ2020 badge MQTT
Copyright Jeroen van Oorschot 2020
https://jjvanoorschot.nl
MIT Licence
"""

import binascii

import appconfig
import display
import keypad
import machine
import system
import time
import touchpads
import wifi
from umqtt.simple import MQTTClient

# Get the settings from the settings menu
APP_NAME = 'homeassistant_cz20_badge'
settings = appconfig.get(APP_NAME, {'MQTT_server_ip': "192.168.1.104",
                                                      'MQTT_device_name': "cz2020",
                                                      'MQTT_discovery_prefix': 'homeassistant',
                                                      'on_press_color': '0xffffff',
                                                      'MQTT_port': 0,
                                                      'MQTT_username': None,
                                                      'MQTT_password': None
                                                      }
                         )
SERVER_IP = settings['MQTT_server_ip']
DEVICE_NAME = settings['MQTT_device_name'].strip('/')
USERNAME = settings['MQTT_username'] or None
PASSWORD = settings['MQTT_password'] or None
PORT = settings['MQTT_port'] or 0
PREFIX = settings['MQTT_discovery_prefix'].strip('/')
try:
    ON_PRESS_COLOR = int(settings['on_press_color'].strip(), 16)
except:
    ON_PRESS_COLOR = 0xffffff
UUID = binascii.hexlify(machine.unique_id()).decode()
NODE_ID = UUID
DEVICE_CONFIG = '{\
"ids": "' + UUID + '",\
"name": "' + DEVICE_NAME + '",\
"sw": "cz2020-badge.team v1",\
"mdl": "CampZone 2020 badge",\
"mf": "badge.team and JeroenvO"\
}'

ORANGE = 0xFF5500
RED = 0xff0000
GREEN = 0x00ff00
COLORS = [[0, 0, 0]] * 16  # save color, brightness for each button.
BRIGHTNESS = [0] * 16  # save brightness for each button.
STATE = [True] * 16  # save state for each button.

# Clear the screen
display.drawFill(0xff0000)
display.flush()


def try_publish(topic, msg):
    global c
    try:
        c.publish(topic, msg)
    except:  # stop app on failure
        try:
            c.disconnect()
        except:
            pass
        system.launcher()


def restart():
    print('restarting app')
    display.drawFill(ORANGE)
    display.flush()
    time.sleep(1)
    system.start(APP_NAME)


def set_color(key_index):
    x, y = key_index % 4, int(key_index / 4)
    if STATE[key_index]:
        cs = [int(c * BRIGHTNESS[key_index] / 255) for c in COLORS[key_index]]
        c_hex = (cs[0] << 16) + (cs[1] << 8) + cs[2]
        display.drawPixel(x, y, c_hex)
    else:
        display.drawPixel(x, y, 0)
    display.flush()


# Key press handler
def on_key(key_index, pressed):
    # print('key event', key_index)
    topic = PREFIX + '/binary_sensor/' + NODE_ID + '/' + str(key_index) + '/state'
    if pressed:
        x, y = key_index % 4, int(key_index / 4)
        try_publish(topic, "ON")
        display.drawPixel(x, y, ON_PRESS_COLOR)  # on press color
        display.flush()
    else:
        try_publish(topic, "OFF")
        set_color(key_index)


# When the home key is pressed, disconnect everything and return to home
def on_home(is_pressed):
    global c
    if is_pressed == 512:
        display.drawFill(RED)
        display.flush()
        for key_index in range(16):  # each button
            topic = PREFIX + '/binary_sensor/' + NODE_ID + '/' + str(key_index) + '/'
            try_publish(topic + "status", "offline")
            topic = PREFIX + '/light/' + NODE_ID + '/' + str(key_index) + '/'
            try_publish(topic + "status", "offline")
        c.disconnect()
        system.launcher()


# When the home key is pressed, disconnect everything and return to home
def on_ok(is_pressed):
    global c
    if is_pressed:
        restart()


# MQTT subscribe handler
def sub_cb(topic, msg):
    # Split the topic into a list. 0=prefix, 1=integration, 2=device, 3=key index
    # integration = int(topic.decode('utf-8').split('/')[1])  # this will always be "light"
    topic = topic.decode('utf-8').split('/')
    key_index = int(topic[3])
    command = topic[4]
    topic_u = PREFIX + '/light/' + NODE_ID + '/' + str(key_index) + '/'
    msg = msg.decode('utf-8')
    if command == 'switch':
        if msg == 'ON':
            STATE[key_index] = True
            set_color(key_index)
            try_publish(topic_u + 'state', 'ON')
        elif msg == 'OFF':
            STATE[key_index] = False
            set_color(key_index)
            try_publish(topic_u + 'state', 'OFF')
        else:
            print('invalid')
    elif command == 'rgb' and topic[5] == 'set':
        COLORS[key_index] = [int(c) for c in msg.split(',')]
        set_color(key_index)
        try_publish(topic_u + 'rgb/state', msg)
    elif command == 'brightness' and topic[5] == 'set':
        BRIGHTNESS[key_index] = int(msg)
        set_color(key_index)
        try_publish(topic_u + 'brightness/state', msg)
    elif topic[0] == 'homeassistant' and topic[1] == 'status':
            print('Hass offline! Rebooting app.')
            restart()


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
display.drawLine(0, 0, 3, 0, GREEN)  # wifi success
display.flush()

# Setup MQTT and connect to it
display.drawLine(0, 1, 3, 1, ORANGE)
display.flush()
c = MQTTClient(UUID, SERVER_IP, port=PORT, user=USERNAME, password=PASSWORD)
c.set_callback(sub_cb)
# Set a last-will
for key_index in range(16):  # each button
    topic = PREFIX + '/binary_sensor/' + NODE_ID + '/' + str(key_index) + '/'
    c.set_last_will(topic + "status", "offline", retain=True)
    topic = PREFIX + '/light/' + NODE_ID + '/' + str(key_index) + '/'
    c.set_last_will(topic + "status", "offline")

# Connect to MQTT server, fail if not possible and return.
if c.connect():
    print("error connecting")
    display.drawLine(0, 1, 3, 1, RED)
    display.flush()
    time.sleep(1)
    system.launcher()

display.drawLine(0, 1, 3, 1, GREEN)  # mqtt success part 1
display.drawLine(0, 2, 3, 2, ORANGE)  # mqtt start part 2
display.flush()

for key_index in range(16):  # each button
    topic = PREFIX + '/binary_sensor/' + NODE_ID + '/' + str(key_index)
    message = '{' + '"name":"{DEVICE_NAME}-{key_index:02d}","stat_t":"~/state","avty_t":"~/status","uniq_id":"{UUID}-btn{key_index}","dev":{DEVICE_CONFIG},"~":"{topic}"'.format(
        key_index=key_index, topic=topic, UUID=UUID, DEVICE_CONFIG=DEVICE_CONFIG, DEVICE_NAME=DEVICE_NAME) + '}'
    try_publish(topic + "config", message)
    try_publish(topic + "status", "online")
    topic = PREFIX + '/light/' + NODE_ID + '/' + str(key_index)
    message = '{' + \
              '"name":"{DEVICE_NAME}-{key_index:02d}-light","stat_t":"~/state","avty_t":"~/status","cmd_t":"~/switch","bri_stat_t":"~/brightness/state","bri_cmd_t":"~/brightness/set","rgb_stat_t":"~/rgb/state","rgb_cmd_t":"~/rgb/set","uniq_id":"{UUID}-btn{key_index}-light","dev":{DEVICE_CONFIG},"ret":true,"~":"{topic}"'. \
                  format(key_index=key_index, topic=topic, UUID=UUID, DEVICE_CONFIG=DEVICE_CONFIG, DEVICE_NAME=DEVICE_NAME) + '}'
    try_publish(topic + "config", message)
    try_publish(topic + "status", "online")

display.drawLine(0, 2, 3, 2, 0x00ff00)  # mqtt finish part 2
display.drawLine(0, 3, 3, 3, ORANGE)  # mqtt part 3
display.flush()

topic = PREFIX + '/light/' + NODE_ID + '/'
c.subscribe(topic + "#")
c.subscribe('homeassistant/status')

display.drawLine(0, 3, 3, 3, GREEN)  # mqtt finish part 2
display.flush()

# Configure the key press handler
keypad.add_handler(on_key)
touchpads.on(touchpads.HOME, on_home)
touchpads.on(touchpads.OK, on_ok)

display.drawFill(0x000000)
display.flush()

while 1:
    try:
        c.wait_msg()
    except Exception as e:
        print('error: ' + str(e))
        try:
            c.disconnect()
        except:
            break
        break
system.launcher()
