 
import touchpads, keypad, display, wifi, audio, time, system, appconfig, machine
from umqtt.simple import MQTTClient
import binascii
# Get the settings from the settings menu
settings = appconfig.get('mqtt_button', {'MQTT_server_ip': "192.168.1.104", 
                                         'MQTT_device_name': "cz2020",
                                         'MQTT_discovery_prefix': 'homeassistant' })
SERVER_IP = settings['MQTT_server_ip']
DEVICE_NAME = settings['MQTT_device_name'].strip('/')
PREFIX = settings['MQTT_discovery_prefix'].strip('/')
UUID = binascii.hexlify(machine.unique_id()).decode()
DEVICE_CONFIG = '{\
    "identifiers": "'+UUID+'",\
    "name": "'+DEVICE_NAME+'",\
    "sw_version": "cz2020-badge.team v0.1",\
    "model": "CZ2020",\
    "manufacturer": "badge.team"\
  }'
COLORS = [int(0xff0000)]*16   # save color for each button.

# Clear the screen
display.drawFill(0xffffff)
display.flush()

# Key press handler
def on_key(key_index, pressed):
    global COLORS, DEVICE_NAME
    x, y = key_index % 4, int(key_index / 4)
    print('key event',key_index)
    topic = PREFIX+'/binary_sensor/'+DEVICE_NAME+'/'+str(key_index)+'/state'
    if(pressed):
        c.publish(topic, "on")
        display.drawPixel(x, y, 0x00FF00)
        display.flush()
    else:
        c.publish(topic, "off")
        display.drawPixel(x, y, COLORS[key_index]) 
        display.flush()

# When the home key is pressed, disconnect everything and return to home
def on_home(is_pressed):
    print('home button: ' + str(is_pressed))
    if(is_pressed == 512):
        c.disconnect()
        wifi.disconnect()
        audio.play('/apps/mqtt_button/wifi_disconnect.mp3')
        time.sleep(6)
        system.launcher()


# MQTT subscribe handler
def sub_cb(topic, msg):
    global COLORS
    print((topic, msg))
    # Split the topic into a list, the last item in the list is the number
    # of the key.
    key_index = int(topic.decode('utf-8').split('/')[-1])
    x, y = key_index % 4, int(key_index / 4)
    try: 
        msg_hex = int(msg.decode('utf-8'), 16)
        COLORS[key_index]=msg_hex  # save color
        display.drawPixel(x, y, msg_hex)
        display.flush()
    except:
        print("Not a Hex number")
        
# Connect to Wi-Fi
if not wifi.status():
    audio.play('/cache/system/wifi_connecting.mp3')
    wifi.connect()
    wifi.wait()
    if not wifi.status():
        audio.play('/cache/system/wifi_failed.mp3')
        time.sleep(6)
        system.launcher()

# Setup MQTT and connect to it
c = MQTTClient("umqtt_client", SERVER_IP)
#c.set_callback(sub_cb)
# Set a last-will 
#c.set_last_will(TOPIC+"available", "offline", retain=True)

# Connect to MQTT server, fail if not possible and return.
audio.play('/apps/mqtt_button/connect_mqtt.mp3')
try:
    c.connect()
    # Make sure the device is "online"
    #c.publish(TOPIC+"available", "online")
    # Subscibe to the "led" topic
    #c.subscribe(TOPIC+"led/#")  # todo mqtt light
    for key_index in range(16):  # each button
        topic = PREFIX+'/binary_sensor/'+DEVICE_NAME+'/'+str(key_index)+'/'
        c.publish(topic+"config", 
                  '{"name": "cz20-btn'+str(key_index)+'", "state_topic":"'+topic+'state", "unique_id":"'+DEVICE_NAME+'-btn'+str(key_index)+'", "device":'+DEVICE_CONFIG+'}')
except:
    audio.play('/apps/mqtt_button/fail_connect_mqtt.mp3')
    time.sleep(6)
    system.launcher()

# Configure the key press handler
keypad.add_handler(on_key)
touchpads.on(touchpads.HOME, on_home)

try:
    while 1:
            c.check_msg()
finally:
    c.disconnect()
    
