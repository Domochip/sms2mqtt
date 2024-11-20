import logging
import time
from datetime import datetime
import os
import signal
import paho.mqtt.client as mqtt
import gammu
import json
import certifi

# callback when the broker responds to our connection request.
def on_mqtt_connect(client, userdata, flags, rc):
    logging.info("Connected to MQTT host")
    client.publish(f"{mqttprefix}/connected", "1", 0, True)
    client.subscribe(f"{mqttprefix}/send")

# callback when the client disconnects from the broker.
def on_mqtt_disconnect(client, userdata, rc):
    logging.info("Disconnected from MQTT host")
    logging.info("Exit")
    exit()

# callback when a message has been received on a topic that the client subscribes to.
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

    for sms in alllinkedsms:
        if sms[0]['UDH']['Type'] == 'NoUDH':
            message = {"datetime":str(sms[0]['DateTime']), "number":sms[0]['Number'], "text":sms[0]['Text']}
            payload = json.dumps(message, ensure_ascii=False)
            client.publish(f"{mqttprefix}/received", payload)
            logging.info(payload)
            try:
                gammusm.DeleteSMS(Folder=0, Location=sms[0]['Location'])
            except Exception as e:
                logging.error(f'ERROR: Unable to delete SMS: {e}')
        elif sms[0]['UDH']['AllParts'] != -1:
            if len(sms) == sms[0]['UDH']['AllParts']:
                decodedsms = gammu.DecodeSMS(sms)
                message = {"datetime":str(sms[0]['DateTime']), "number":sms[0]['Number'], "text":decodedsms['Entries'][0]['Buffer']}
                payload = json.dumps(message, ensure_ascii=False)
                client.publish(f"{mqttprefix}/received", payload)
                logging.info(payload)
                for part in sms:
                    gammusm.DeleteSMS(Folder=0, Location=part['Location'])
            else:
                logging.info(f"Incomplete Multipart SMS ({len(sms)}/{sms[0]['UDH']['AllParts']}): waiting for parts")
        else:
            logging.info('***************** Unsupported SMS type *****************')
            logging.info('===============sms=================')
            logging.info(sms)
            logging.info('===============decodedsms=================')
            decodedsms = gammu.DecodeSMS(sms)
            logging.info(decodedsms)
            logging.info('================================')
            gammusm.DeleteSMS(Folder=0, Location=sms[0]['Location'])
            
# function used to obtain signal quality        
def get_signal_info():
    global old_signal_info
    try:
        signal_info = gammusm.GetSignalQuality()
        if signal_info != old_signal_info:
            signal_payload = json.dumps(signal_info)
            client.publish(f"{mqttprefix}/signal", signal_payload)
            old_signal_info = signal_info
    except Exception as e:
        logging.error(f'ERROR: Unable to check signal quality: {e}')

old_signal_info = ""



# function used to obtain battery charge
def get_battery_charge():
    global old_battery_charge
    try:
        battery_charge = gammusm.GetBatteryCharge()
        if battery_charge != old_battery_charge:
            battery_payload = json.dumps(battery_charge)
            client.publish(f"{mqttprefix}/battery", battery_payload)
            old_battery_charge = battery_charge
    except Exception as e:
        logging.error(f'ERROR: Unable to check battery charge: {e}')

old_battery_charge = ""

# function used to obtain network info
def get_network_info():
    global old_network_info
    try:
        network_info = gammusm.GetNetworkInfo()
        if network_info != old_network_info:
            network_payload = json.dumps(network_info)
            client.publish(f"{mqttprefix}/network", network_payload)
            old_network_info = network_info
    except Exception as e:
        logging.error(f'ERROR: Unable to check network info: {e}')

old_network_info = ""

# function used to obtain datetime
def get_datetime():
    global old_time
    try:
        now = gammusm.GetDateTime().timestamp()
        if (now - old_time) > 60:
            client.publish(f"{mqttprefix}/datetime", now)
            old_time = now
    except Exception as e:
        logging.error(f'ERROR: Unable to check datetime: {e}')

old_time = time.time()

def shutdown(signum=None, frame=None):
    client.publish(f"{mqttprefix}/connected", "0", 0, True)
    client.disconnect()

def setup_mqtt_ssl(client, use_tls=False):
    try:
        if use_tls:
            client.tls_set(ca_certs=certifi.where())
            logging.info("SSL/TLS configured successfully")
        else:
            logging.info("Connecting without SSL/TLS")
    except Exception as e:
        logging.error(f"Error configuring SSL/TLS: {e}")
        exit(1)

if __name__ == "__main__":
    logging.basicConfig( format="%(asctime)s: %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    versionnumber='1.4.6'

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
    gammuoption = os.getenv("GAMMUOPTION","")
    moreinfo = bool(os.getenv("MOREINFO"))
    heartbeat = bool(os.getenv("HEARTBEAT"))
    mqttprefix = os.getenv("PREFIX","sms2mqtt")
    mqtthost = os.getenv("HOST","localhost")
    mqttport = int(os.getenv("PORT",1883))
    mqttclientid = os.getenv("CLIENTID","sms2mqtt")
    mqttuser = os.getenv("USER")
    mqttpassword = os.getenv("PASSWORD")
    use_tls = str(os.getenv("USETLS", "")).lower() in ('true', '1', 'yes')

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    gammurcfile = open("/app/gammurc", 'w')
    gammurcfile.write(f"""
[gammu]
device = {device}
connection = at
{gammuoption}
""")
    gammurcfile.close()

    gammusm = gammu.StateMachine()
    gammusm.ReadConfig(Filename="/app/gammurc")
    gammusm.Init()

    if gammusm.GetSecurityStatus() == 'PIN':
        gammusm.EnterSecurityCode('PIN',pincode)

    versionTuple = gammu.Version()
    logging.info(f'Gammu runtime: v{versionTuple[0]}')
    logging.info(f'Python-gammu runtime: v{versionTuple[1]}')
    logging.info(f'Manufacturer: {gammusm.GetManufacturer()}')
    logging.info(f'IMEI: {gammusm.GetIMEI()}')
    logging.info(f'SIMIMSI: {gammusm.GetSIMIMSI()}')    

    if heartbeat:
        gammusm.SetDateTime(datetime.now())

    logging.info('Gammu initialized')

    client = mqtt.Client(mqttclientid)
    client.username_pw_set(mqttuser, mqttpassword)
    setup_mqtt_ssl(client,use_tls)
    client.on_connect = on_mqtt_connect
    client.on_disconnect = on_mqtt_disconnect
    client.on_message = on_mqtt_message
    client.will_set(f"{mqttprefix}/connected", "0", 0, True)
    client.connect(mqtthost, mqttport)

    while True:
        time.sleep(1)
        loop_sms_receive()
        get_signal_info()
        if moreinfo:
            get_battery_charge()
            get_network_info()
        if heartbeat:
            get_datetime()
        client.loop()
