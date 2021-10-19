# Prerequisites

You need a GSM dongle "compatible" with Gammu : https://wammu.eu/phones/  
Even if your dongle is not listed, it should works with.

If you need specific gammu settings to be added, feel free to open a PR or an issue.

# How does it work

![Diagram](https://raw.githubusercontent.com/Domochip/sms2mqtt/master/diagram.svg)

# How-to
## Install
For Docker, run it by executing the following commmand:

```bash
docker run \
    -d \
    --name sms2mqtt \
    --restart=always \
    --device=/dev/ttyUSB0:/dev/mobile \
    -e PIN="1234" \
    -e HOST="192.168.1.x" \
    -e PORT=1883 \
    -e PREFIX="sms2mqtt" \
    -e CLIENTID="sms2mqttclid" \
    -e USER="usr" \
    -e PASSWORD="pass" \
    domochip/sms2mqtt
```
For Docker-Compose, use the following yaml:

```yaml
version: '3'
services:
  sms2mqtt:
    container_name: sms2mqtt
    image: domochip/sms2mqtt
    devices:
    - /dev/serial/by-id/usb-HUAWEI_HUAWEI_Mobile-if00-port0:/dev/mobile
    environment:
    - PIN=1234
    - HOST=10.0.0.2
    - PORT=1883
    - PREFIX=sms2mqtt
    - CLIENTID=sms2mqttclid
    - USER=mqtt_username
    - PASSWORD=mqtt_password
    restart: always
```

### Configure

#### Device
* `device`: Location of GSM dongle (replace /dev/ttyUSB0 with yours), it need to be mapped to /dev/mobile

*NOTE: The `/dev/ttyUSBx` path of your GSM modem could change on reboot, so it's recommended to use the `/dev/serial/by-id/` path or symlink udev rules to avoid this issue.*

#### Environment variables
* `PIN`: **Optional**, Pin code of your SIM
* `HOST`: IP address or hostname of your MQTT broker
* `PORT`: **Optional**, port of your MQTT broker
* `PREFIX`: **Optional**, MQTT prefix used in topics for subscribe/publish
* `CLIENTID`: **Optional**, MQTT client id to use
* `USER`: **Optional**, MQTT username
* `PASSWORD`: **Optional**, MQTT password

## Send

The default {prefix} for topics is sms2mqtt.  

To send SMS: 
1. Publish this payload to topic **sms2mqtt/send** :  
`{"number":"+33612345678", "text":"This is a test message"}`  
2. SMS is sent  
3. A confirmation is sent back through MQTT to topic **sms2mqtt/sent** :  
`{"result":"success", "datetime":"2021-01-23 13:00:00", "number":"+33612345678", "text":"This is a test message"}`  
  
- ✔️ SMS to multiple Numbers using semicolon (;) seperated list. A confirmation will be sent back for each numbers.
- ✔️ very long messages (more than 160 char).
- ✔️ unicode messages containing emoji like : `{"number":"+33612345678", "text":"It's working fine 👌"}`
- ✔️ very long messages containing emoji

## Receive

Received SMS are published to topic **sms2mqtt/received** like this :  
`{"datetime":"2021-01-23 13:30:00", "number":"+31415926535", "text":"Hi, Be the Pi with you"}`  

- ✔️ long SMS messages
- ❌ any MMS

## Other topics

- **sms2mqtt/signal**: A signal quality payload is published when quality change
 E.g. `{"SignalStrength": -71, "SignalPercent": 63, "BitErrorRate": -1}`

 - **sms2mqtt/battery**: A payload with information on battery status and charge is published for each change
 E.g. `{"BatteryPercent": 100, "ChargeState": "BatteryPowered", "BatteryVoltage": -1, "ChargeVoltage": -1, "ChargeCurrent": -1, "PhoneCurrent": -1, "BatteryTemperature": -1, "PhoneTemperature": -1, "BatteryCapacity": -1}`

 - **sms2mqtt/network**: A payload with network information is published for each change
 E.g. `{"NetworkName": "", "State": "HomeNetwork", "PacketState": "HomeNetwork", "NetworkCode": "392 11", "CID": "74C5", "PacketCID": "74C5", "GPRS": "Attached", "PacketLAC": "8623", "LAC": "8623"}`

 - **sms2mqtt/connected**: Connection status (1 = Connected / 0 = Disconnected)
 E.g. `1`

# Troubleshoot
## Logs
You need to have a look at logs using :  
`docker logs sms2mqtt`

# Updating
To update to the latest Docker image:
```bash
docker stop sms2mqtt
docker rm sms2mqtt
docker rmi domochip/sms2mqtt
# Now run the container again, Docker will automatically pull the latest image.
```
# Ref/Thanks

I want to thanks those repositories for their codes that inspired me :  
* https://github.com/pajikos/sms-gammu-gateway
* https://github.com/pkropf/mqtt2sms 
