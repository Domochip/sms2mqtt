import logging
import time
import os
import paho.mqtt.client as mqtt
import gammu
import json


# The callback for when the client receives a CONNACK response from the server.
def on_mqtt_connect(client, userdata, flags, rc):
    logging.info("Connected to MQTT host")
    client.publish(f"{mqttprefix}/connected", "1")
    client.subscribe(f"{mqttprefix}/send")

# The callback for when a PUBLISH message is received from the server.
def on_mqtt_message(client, userdata, msg):
    try:
        logging.info(f'MQTT received : {msg.payload}')
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload, strict=False)
    except Exception as e:
        logging.error(f'failed to decode JSON, reason: {e}, string: {msg.payload}')

    for key, value in data.items():
        if key.lower() == 'number':
            number=value
        if key.lower() == 'text':
            text=value

    if not number:
        logging.error('no number to send to')
        return False

    if not text:
        logging.error('no text body to send')
        return False

    for num in (number.split(";")):
        num = num.replace(' ','')
        if num == '':
            continue

        smsinfo = {
            'Class': -1,
            'Entries': [{
                'ID': 'ConcatenatedAutoTextLong',
                'Buffer' : text
            }]
        }

        try:
            logging.info(f'Sending SMS To {num} containing {text}')
            encoded = gammu.EncodeSMS(smsinfo)
            for message in encoded:
                message['SMSC'] = {'Location': 1}
                message['Number'] = num
                gammusm.SendSMS(message)
            feedback = {"result":"success", "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "number":num, "text":text}
            client.publish(f"{mqttprefix}/sent", json.dumps(feedback))
            logging.info(f'SMS sent to {num}')
        except Exception as e:
            feedback = {"result":f'error : {e}', "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "number":num, "text":text}
            client.publish(f"{mqttprefix}/sent", json.dumps(feedback))
            logging.error(feedback['result'])

# function used to parse received sms
def loop_sms_receive():

    # process Received SMS
    status = gammusm.GetSMSStatus()
    remain = status['SIMUsed'] + status['PhoneUsed'] + status['TemplatesUsed']
    # logging.info(f"SIMUsed : {status['SIMUsed']}, PhoneUsed : {status['PhoneUsed']}, TemplatesUsed : {status['TemplatesUsed']}")
    if remain > 0: logging.info(f'{remain} SMS received')
    while remain > 0:
        sms = gammusm.GetNextSMS(Folder=0, Start=True)
        message = {"datetime":str(sms[0]['DateTime']), "number":sms[0]['Number'], "text":sms[0]['Text']}
        payload = json.dumps(message)
        client.publish(f"{mqttprefix}/received", payload)
        logging.info(payload)
        gammusm.DeleteSMS(Folder=0, Location=sms[0]['Location'])
        remain -= 1


if __name__ == "__main__":
    logging.basicConfig( format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    # devmode is used to start container but not the code itself, then you can connect interactively and run this script by yourself
    # docker exec -it sms2mqtt /bin/sh
    if os.getenv("DEVMODE",0) == "1":
        logging.info('DEVMODE mode : press Enter to continue')
        try:
            input()
            logging.info('')
        except EOFError as e:
            # EOFError means we're not in interactive so loop forever
            while 1:
                time.sleep(3600)


    device = os.getenv("DEVICE","/dev/mobile")
    pincode = os.getenv("PIN")
    mqttprefix = os.getenv("PREFIX","sms2mqtt")
    mqtthost = os.getenv("HOST","localhost")
    mqttport = os.getenv("PORT",1883)
    mqttclientid = os.getenv("CLIENTID","sms2mqtt")
    mqttuser = os.getenv("USER")
    mqttpassword = os.getenv("PASSWORD")

    gammurcfile = open("/app/gammurc", 'w')
    gammurcfile.write(f"""
[gammu]
device = {device}
connection = at
""")
    gammurcfile.close()

    gammusm = gammu.StateMachine()
    gammusm.ReadConfig(Filename="/app/gammurc")
    gammusm.Init()

    if gammusm.GetSecurityStatus() == 'PIN':
        gammusm.EnterSecurityCode('PIN',pincode)

    logging.info('Gammu initialized')

    client = mqtt.Client(mqttclientid, mqttport)
    client.username_pw_set(mqttuser, mqttpassword)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.will_set(f"{mqttprefix}/connected", "0")
    client.connect(mqtthost)
    
    run = True
    while run:
        time.sleep(1)
        loop_sms_receive()
        client.loop()
