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
    level=logging.INFO,
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

def callapspotapi(action, message, callsign=None):
    response = []
    if action == "spot":
        logging.info('Got a SPOT request for the API, checking destination')
        if message[0] in ["POTA","WWFF","SOTA","SIOTA"]:
            if message[0] == "POTA":
                logging.info('Message destination is POTA, setting up the call to the API to send to pota')
                pota_full_url = APSPOTAPIURL + '/spot/pota' + '?callsign=' + callsign + '&ref=' + urllib.parse.quote_plus(message[1]) + '&freq=' + urllib.parse.quote_plus(message[2]) + '&mode=' + message[3] + '&comment=' + urllib.parse.quote_plus(getcomment(message))
                logging.info(pota_full_url)
                potaspot = requests.get(pota_full_url)
                if potaspot.status_code == 200:
                    logging.info('Got a 200 response from the API, add response message')
                    logging.info(potaspot.text)
                    response.append(json.loads(potaspot.text)['response'])
                else:
                    logging.info('Got a non 200 response from the API, error out')
                    logging.info(potaspot)
                    response.append("Failed posting spot to pota.app")
            if message[0] in ["WWFF","SOTA","SIOTA"] or (message[0] == "POTA" and message[1].startswith('VK')):
                pnp_full_url = APSPOTAPIURL + '/spot/pnp' + '?pnpSpotType=' + message[0] + '&callsign=' + callsign + '&ref=' + urllib.parse.quote_plus(message[1]) + '&freq=' + urllib.parse.quote_plus(message[2]) + '&mode=' + message[3] + '&comment=' + urllib.parse.quote_plus(getcomment(message))
                logging.info(pnp_full_url)
                pnpspot = requests.get(pnp_full_url)
                if pnpspot.status_code == 200:
                    logging.info('Got a 200 response from the API, add response message')
                    response.append(json.loads(pnpspot.text)['response'])
                else:
                    logging.info('Got a non 200 response from the API, error out')
                    response.append("Failed posting spot to parksnpeaks.org")
        else:
            response.append("Target not supported")
    elif action == "spots":
        logging.info(message)
        logging.info(message[0].lower())

        numSpots = 3
        mode = "ALL"   

        secondCommand = get_val(message, 1, "NONE")
        if secondCommand != "NONE":
            try:
                numSpots = int(secondCommand)
                if int(numSpots) > 5: numSpots = 5
            except:
                mode = secondCommand
                thirdCommand = get_val(message, 2, "NONE")
                try:
                    numSpots = int(thirdCommand)
                    if int(numSpots) > 5: numSpots = 5
                except:
                    pass

        spots = requests.get(APSPOTAPIURL + '/spots/' + message[0].lower() + '?numSpots=' + str(numSpots) + '&mode=' + mode)
        logging.info(json.loads(spots.text)['response'])
        response.extend(json.loads(spots.text)['response'])

    elif action == "search":
        response.append("Search not implemented yet")
    return response
    

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

def sendusage(message, destination):
    try:
        for usagemessage in USAGESTRING[message]:
            time.sleep(messageDelay)
            sendmessage(usagemessage, destination)
    except:
        sendmessage("ERROR: \"" + message + "\" NOT SUPPORTED", destination)
        time.sleep(messageDelay)
        sendmessage("SEND \"USAGE\" FOR MORE INFO", destination)

def validatemessage(message):
    logging.info('Validating Message')
    logging.debug(message)
    #Check we have the right number of strings
    if len(message) > 4:
        logging.info("Valid Spot Message Length")
    else:
        if message.split('.') > 1:
            logging.info('ERROR: VALIDATION FAILED: USER USING DOTS NOT SPACES')
            return "INVALID SPOT - PLEASE USE SPACES NOT DOTS"
        else:
            logging.info('ERROR: VALIDATION FAILED: INVALID SPOT MESSAGE')
            return "INVALID SPOT - FORMAT: \"! <Target> <Ref> <Freq> <Mode> <Comment>\""
    #Check we have a valid frequency - This could do with some work to verify within HAM bands      
    if isfloat(message[2]):
        logging.info("Valid Frequency " + message[3])
    else:
        logging.info('ERROR: VALIDATION FAILED: INVALID FREQUENCY')
        return "ERROR: INVALID FREQUENCY - MUST BE DECIMAL"
    #Check to see if the modes are within the expected modes
    if message[3] in ["SSB", "CW", "AM", "FM", "DATA", "PSK", "RTTY"]:
        logging.info('Valid Mode ' + message[3])
    elif message[3] in ["FT8"] and message[1] == "POTA":
        logging.info('Valid mode ' + message[3] + ' for POTA')
    else:
        logging.info('ERROR: VALIDATION FAILED: INVALID MODE')
        return "ERROR: INVALID MODE - MUST BE SSB|CW|AM|FM|DATA"
    logging.info('Valid Message')
    return True

def sendspot(message, fromcallsign):
    logging.info('Now we need to see if we got a valid SPOT message')
    messagecheck = validatemessage(message)
    if messagecheck == True:
        logging.info('Got a valid SPOT message so process the message')
        global messageCache
        if ' '.join(map(str, message)) not in messageCache.get(hash(fromcallsign + ' '.join(message)), ""):
            messageCache[hash(fromcallsign + ' '.join(message))] = ' '.join(message)
            friendlycallsign = fromcallsign.split('-')[0]
            logging.info('Sending spot to API')
            response = callapspotapi("spot", message, friendlycallsign)
            logging.info('Got response from API:')
            logging.info(response)
            logging.info('Sending response over APRS')
            for response in response:
                sendmessage(response, fromcallsign)
                time.sleep(messageDelay)
        else:
            logging.info('ERROR: Message ' + ' '.join(message) + ' has already been seen in the last half hour')
            sendmessage('ERROR: Duplicate message detected', fromcallsign)
    else:
        logging.info('ERROR: Invalid spot message, send result of message validation check to user')
        sendmessage(messagecheck, fromcallsign)

def sendspots(message, fromcallsign):
    logging.info('Sending spots request to API')
    response = callapspotapi("spots", message)
    logging.info('Got response from API:')
    logging.info(response)
    logging.info('Sending response over APRS')
    for spot in response:
        sendmessage(spot, fromcallsign)
        time.sleep(messageDelay)

def search(messaage, fromcallsign):
    logging.info('Sending search request to API')
    response = callapspotapi("search", message)
    logging.info('Got response from API:')
    logging.info(response)
    logging.info('Sending response over APRS')
    for ref in response:
        sendmessage('FOUND: ' + ref, fromcallsign)
        time.sleep(messageDelay)

def incomingMessage(packet):
    message = aprslib.parse(packet)
    logging.info('Got message from APRS ' + str(message))
    if (message.get('message_text')):
        logging.info('We have a message so send an ack')
        if message.get('msgNo'):
            sendack(message['from'], message['msgNo'])
            time.sleep(messageDelay)
        messagetext = message['message_text'].upper()
        if messagetext.startswith("!"):
            sendspot(messagetext.split()[1:], message['from'])
        elif messagetext.startswith('SPOTS'):
            sendspots(messagetext.split()[1:], message['from'])
        elif messagetext.startswith('?'):
            search(messagetext.split()[1:], message['from'])
        else:
            logging.info('Sending usage information')
            sendusage(message['message_text'].upper(), message['from'])
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