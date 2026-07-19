import aprslib
import logging
import requests
import json
import cachetools
import os
import time
import threading
import urllib.parse
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

messageNo = 0
messageDelay = 1.5
retryAttempts = 5

messageCache = cachetools.TTLCache(maxsize=99999, ttl=1800)
ackCache = cachetools.TTLCache(maxsize=99999, ttl=(60 * (retryAttempts + 1)))

CALLSIGN = os.getenv('CALLSIGN')
PASSCODE = os.getenv('PASSCODE')
APSPOTAPIURL = os.getenv('APSPOTAPIURL')

USAGESTRING = {
    "USAGE": [
        "APSPOT USAGE INFORMATION - 6 MSGS",
        "TO SPOT SEND: \"! <Target> <Ref> <Freq> <Mode> <Comment>\" WITHOUT QUOTES",
        "TO GET SPOTS SEND: \"SPOTS TARGET\" | REQUESTS ARE CASE INSENSITIVE",
        "VALID TARGETS: SOTA, WWFF, POTA, SIOTA",
        "FOR MORE HELP SEND USAGE <Target> EG:\"USAGE WWFF\"",
        "INCLUDE \"APTEST\" IN COMMENT AND SPOT WILL NOT BE POSTED"
    ],
    "USAGE WWFF": [
        "EXAMPLE: \"! WWFF VKFF-1929 7.144 SSB CQCQ\""
    ],
    "USAGE SOTA": [
        "EXAMPLE: \"! SOTA VK3/VN-030 7.090 SSB QCQ\""
    ],
    "USAGE SIOTA": [
        "EXAMPLE: \"! SIOTA VK-YNE5 7.090 SSB CQCQ\""
    ],
    "USAGE POTA": [
        "EXAMPLE: \"! POTA VK-3024 7.195 SSB CQCQ\""
    ]
}

AIS = aprslib.IS(CALLSIGN, passwd=PASSCODE)
AIS.set_filter('g/' + CALLSIGN)
AIS.set_server('aunz.aprs2.net', 14580)

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

def getcomment(message):
    try:
        return ' '.join(message[4:]) + " [APSPOT]"
    except:
        return "[APSPOT]"

def get_val(myList, idx, default):
    try:
        return myList[idx]
    except IndexError:
        return default

def sendmessage(message, destination):
    threading.Thread(target=sendmessagethread, args=[message,destination]).start()

def sendmessagethread(message, destination):
    global messageNo
    global ackCache
    global retryAttempts
    if messageNo == 99999: messageNo = 0
    messageNo += 1
    activeMessageNo = messageNo
    RESPONSEMESSAGE = CALLSIGN + '>' + destination + ',TCPIP::' + "{:<9}".format(destination) + ':' + message + '{' + str(activeMessageNo).zfill(5)
    logging.info('Sending response to APRS User ' + RESPONSEMESSAGE)
    AIS.sendall(RESPONSEMESSAGE)
    ackCache[str(activeMessageNo).zfill(5)] = False
    logging.info('Waiting for Ack for message ' + str(activeMessageNo).zfill(5))
    time.sleep(60)
    messageAttempts = 1
    logging.info('Checking for Ack for message ' + str(activeMessageNo).zfill(5))
    while (ackCache[str(activeMessageNo).zfill(5)] == False) and (messageAttempts < retryAttempts):
        messageAttempts += 1
        logging.info('No Ack received for message ' + str(activeMessageNo).zfill(5) + ' ... Retrying, Attempt: ' + str(messageAttempts))
        AIS.sendall(RESPONSEMESSAGE)
        time.sleep(60)
    if ackCache[str(activeMessageNo).zfill(5)] == False:
        logging.info('No ack received after 5 attempts for message ' + str(activeMessageNo).zfill(5) + ', exiting')
    else:
        logging.info('Ack received for message ' + str(activeMessageNo).zfill(5) + ' after ' + str(messageAttempts) + ' Attempts')

def sendack(destination, msgNo):
    ACK = CALLSIGN + '>' + destination + ',TCPIP::' + "{:<9}".format(destination) + ':ack' + msgNo
    logging.info('Sending '+ ACK)
    AIS.sendall(ACK)

def sendstatus():
    try:
        while True:
            logging.info('Sending in updated comment Message')
            now = datetime.now()
            AIS.sendall(CALLSIGN + '>APRS,TCPIP:>APSPOT Spotting Gateway Online ' + now.strftime("%Y%m%d%H%M"))
            time.sleep(60)
    except Exception as e:
        logging.error(e)
        return

def processmessage(action, message, activator=""):
    logging.info("Detemine Message Type")
    logging.info("Got a " + action + " message")
    response = []
    if action == "spot":
        logging.info("Preparing spot URL")
        url = APSPOTAPIURL + '/processmessage?action=spot&activator=' + activator + '&message=' + urllib.parse.quote_plus(message)
        logging.info(url)
    else:
        logging.info("Preparing " + action + " URL")
        url = APSPOTAPIURL + '/processmessage?action=' + action + '&message=' + urllib.parse.quote_plus(message)
        logging.info(url)
    apiresponse = requests.get(str(url), timeout=10)
    logging.debug(apiresponse)
    if apiresponse.status_code == 200:
        logging.debug(apiresponse.text)
        for result in json.loads(apiresponse.text)['response']:
            response.append(result)
    else:
        response.append("ERROR CONNECTING TO APSPOT API")
    return response

def incomingMessage(packet):
    message = aprslib.parse(packet)
    logging.info('Got message from APRS ' + str(message))
    if (message.get('message_text')):
        if '\x00' in message.get('message_text'):
            logging.info('Invalid APRS Message. Dropping')
        else:
            logging.info('We have a message so send an ack')
            if message.get('msgNo'):
                sendack(message['from'], message['msgNo'])
                time.sleep(messageDelay)
            messagetext = message['message_text'].upper()
            if messagetext.startswith("!"):
                response = processmessage("spot", messagetext[2:], message['from'].split("-")[0])
            elif messagetext.startswith('SPOTS'):
                response = processmessage("spots", messagetext[6:])
            elif messagetext.startswith('?'):
                logging.info("Processing Message")
                response = processmessage("search", messagetext[2:])
            else:
                logging.info('Sending usage information')
                response = processmessage("usage", messagetext[6:])
            logging.debug(response)
            for result in response:
                sendmessage(result, message['from'])
                time.sleep(messageDelay)
    elif message.get('response') == 'ack':
        global ackCache
        logging.info('Got an ack for message ' + message.get('msgNo'))
        ackCache[message.get('msgNo')] = True
    else:
        logging.info("Not an valid message. Dropping")

def connectaprs():
    AIS.connect()
    logging.info('Sending in status message')
    AIS.sendall(CALLSIGN + '>APRS,TCPIP:=3351.21S/15113.42E$APSPOT Spotting Gateway visit: https://apspot.radio/')
    statusthread = threading.Thread(target=sendstatus)
    statusthread.start()
    AIS.consumer(incomingMessage, raw=True, immortal=True)
    
while True:
    try:
        connectaprs()
    except Exception as e:
        logging.error(e)
        logging.error('ERROR: APRS Connection Lost, Reconnecting')