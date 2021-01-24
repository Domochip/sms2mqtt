# Prerequisites

You need a GSM dongle "compatible" with Gammu : https://wammu.eu/phones/  
Even if your dongle is not listed, it should works with.

If you need specific gammu settings to be added, feel free to open a PR or an issue.

# How does it work

![Diagram](https://raw.githubusercontent.com/Domochip/sms2mqtt/master/diagram.svg)

# How-to
## Install

Run by executing the following commmand:

```bash
docker run \
    -d \
    --name sms2mqtt \
    --restart=always \
    --device=/dev/ttyUSB0:/dev/mobile \
    -e HOST="192.168.1.x" \
    domochip/sms2mqtt
```

### Parameters explanation
* `--device=/dev/ttyUSB0:/dev/mobile`: Location of GSM dongle (replace /dev/ttyUSB0 with yours), it need to be mapped to /dev/mobile
* `-e PIN="1234"`: **Optional**, Pin code of your SIM
* `-e HOST="192.168.1.x"`: IP address or hostname of your MQTT broker
* `-e PORT=1883`: **Optional**, port of your MQTT broker
* `-e PREFIX="sms2mqtt"`: **Optional**, prefix used in topics for subscribe/publish
* `-e CLIENTID="sms2mqttclid"`: **Optional**, MQTT client id to use
* `-e USER="usr"`: **Optional**, MQTT user name
* `-e PASSWORD="pass"`: **Optional**, MQTT password

## Send

The default {prefix} for topics is sms2mqtt.  

To send SMS: 
1. Publish this payload to topic **sms2mqtt/send** :  
`{"number":"+33612345678", "text":"This is a test message"}`  
2. SMS is sent  
3. A confirmation is send back through MQTT to topic **sms2mqtt/sent** :  
`{"result":"success", "datetime":"2021-01-23 13:00:00", "number":"+33612345678", "text":"This is a test message"}`  
  
- [x] You can send SMS to multiple Numbers using semicolon (;) seperated list. A confirmation will be sent back for each numbers.
- [x] You cand send very long messages (more than 160 char).
- [X] You can send unicode messages containing emoji like : `{"number":"+33612345678", "text":"It's work fine 👌"}`
- [X] You can send very long messages containing emoji

## Receive

Received SMS are published to topic **sms2mqtt/received** like this :  
`{"datetime":"2021-01-23 13:30:00", "number":"+31415926535", "text":"Hi, Be the Pi with you"}`

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
* https://github.com/pajikos/sms-gammu-gateway : I have a Huawei dongle and I found out that gammu 1.39 works fine with it 👌
* https://github.com/pkropf/mqtt2sms 
