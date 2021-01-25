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
        feedback = {"result":f'error : failed to decode JSON ({e})', "payload":payload}
        client.publish(f"{mqttprefix}/sent", json.dumps(feedback, ensure_ascii=False))
        logging.error(f'failed to decode JSON ({e}), payload: {msg.payload}')
        return

    for key, value in data.items():
        if key.lower() == 'number':
            number=value
        if key.lower() == 'text':
            text=value

    if 'number' not in locals() or not isinstance(number, str) or not number:
        feedback = {"result":'error : no number to send to', "payload":payload}
        client.publish(f"{mqttprefix}/sent", json.dumps(feedback, ensure_ascii=False))
        logging.error('no number to send to')
        return False

    if 'text' not in locals() or not isinstance(text, str):
        feedback = {"result":'error : no text body to send', "payload":payload}
        client.publish(f"{mqttprefix}/sent", json.dumps(feedback, ensure_ascii=False))
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
            client.publish(f"{mqttprefix}/sent", json.dumps(feedback, ensure_ascii=False))
            logging.info(f'SMS sent to {num}')
        except Exception as e:
            feedback = {"result":f'error : {e}', "datetime":time.strftime("%Y-%m-%d %H:%M:%S"), "number":num, "text":text}
            client.publish(f"{mqttprefix}/sent", json.dumps(feedback, ensure_ascii=False))
            logging.error(feedback['result'])

# function used to parse received sms
def loop_sms_receive():

    # process Received SMS
    allsms = []
    start=True
    while True:
        try:
            if start:
                sms = gammusm.GetNextSMS(Folder=0, Start=True)
                start=False
            else:
                sms = gammusm.GetNextSMS(Folder=0, Location=sms[0]['Location'])
            allsms.append(sms)
        except gammu.ERR_EMPTY as e:
            break

    if not len(allsms):
        return
    
    alllinkedsms=gammu.LinkSMS(allsms)

    logging.info(f'{len(alllinkedsms)} SMS received')

    for sms in allsms:
        if sms[0]['UDH']['Type'] == 'NoUDH' or sms[0]['UDH']['AllParts'] == -1:
            message = {"datetime":str(sms[0]['DateTime']), "number":sms[0]['Number'], "text":sms[0]['Text']}
            payload = json.dumps(message, ensure_ascii=False)
            client.publish(f"{mqttprefix}/received", payload)
            logging.info(payload)
            gammusm.DeleteSMS(Folder=0, Location=sms[0]['Location'])


if __name__ == "__main__":
    logging.basicConfig( format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    versionnumber='1.1.0'

    logging.info(f'===== sms2mqtt v{versionnumber} =====')

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
