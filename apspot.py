import aprslib
import logging
import requests
import json
import cachetools
import os
import time
import threading
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

cache = cachetools.TTLCache(10000, ttl=172800)

messageNo = 0

CALLSIGN = os.getenv('CALLSIGN')
PASSCODE = os.getenv('PASSCODE')
PNPURL = os.getenv('PNPURL')
PNPUSERID = os.getenv('PNPUSERID')
PNPAPIKEY = os.getenv('PNPAPIKEY')
SOTAURL = os.getenv('SOTAURL')
SOTAUSER = os.getenv('SOTAUSER')
POTAURL = os.getenv('POTAURL')
DEVPOTAURL = os.getenv('DEVPOTAURL')

USAGESTRING = {
    "USAGE": [
        "APSPOT USAGE INFORMATION - 6 MSGS",
        "USAGE: TO SEND: \"! <Target> <Ref> <Freq> <Mode> <Comment>\" WITHOUT QUOTES",
        "USAGE: TO GET SPOTS: \"SPOTS TARGET\" | REQUESTS ARE CASE INSENSITIVE",
        "VALID TARGETS: SOTA, WWFF, POTA, SIOTA",
        "FOR MORE HELP SEND USAGE <Target> EG:\"USAGE WWFF\"",
        "INCLUDE \"TEST\" IN COMMENT AND SPOT WILL NOT BE POSTED"
    ],
    "USAGE WWFF": [
        "EXAMPLE: \"! WWFF VKFF-1929 7.144 SSB CQCQ\'"
    ],
    "USAGE SOTA": [
        "EXAMPLE: \"! SOTA VK3/VN-030 7.090 SSB QCQ\'"
    ],
    "USAGE SIOTA": [
        "EXAMPLE: \"! SIOTA VK-YNE5 7.090 SSB CQCQ\'"
    ],
    "USAGE POTA": [
        "EXAMPLE: \"! POTA VK-3024 7.195 SSB CQCQ\'"
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
def getcomment(spotinfo):
    try:
        return ' '.join(spotinfo[5:]) + "[APSPOT]"
    except:
        return "[APSPOT]"

def extract_potaid(json):
    try:
        # Also convert to int since update_time will be string.  When comparing
        # strings, "10" is smaller than "2".
        return int(json['spotId'])
    except KeyError:
        return 0

def sendmessage(message, destination):
    global messageNo
    if messageNo == 999: messageNo = 0
    messageNo += 1
    RESPONSEMESSAGE = CALLSIGN + '>' + destination + ',TCPIP::' + "{:<9}".format(destination) + ':' + message + '{' + str(messageNo).zfill(4)
    logging.info('Sending response to APRS User ' + RESPONSEMESSAGE)
    AIS.sendall(RESPONSEMESSAGE)

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
            sendmessage(usagemessage, destination)
    except:
        sendmessage("ERROR: \"" + message + "\" NOT SUPPORTED", destination)
        sendmessage("SEND \"USAGE\" FOR MORE INFO", destination)

def validatecall_pnp(callsign):
    logging.info('Getting callsign database from PNP')
    callsigns=requests.get(PNPURL + '/callsign/', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if callsigns.status_code == 200:
        if callsign in callsigns.text:
            logging.info('CALLSIGN VALIDATED')
            return True
        else:
            logging.info('ERROR: CALLSIGN VALIDATION FAILED, NOT IN PNP DATABASE')
            return "ERROR: UNABLE TO SPOT: CALLSIGN NOT IN PNP DATABASE"
    else:
        logging.info('ERROR: CALLSIGN VALIDATION FAILED, PNP CALLSIGN DATABASE UNAVAILABLE')
        return "ERROR: UNABLE TO SPOT: PNP CALLSIGN DATABASE UNAVAILABLE"

def validatecall_pota(callsign):
    logging.info('Getting callsign database from POTA')
    callsigns=requests.get(POTAURL + '/stats/user/' + callsign)
    match callsigns.status_code:
        case 200:
            if callsign in callsigns.text:
                logging.info('CALLSIGN VALIDATED')
                return True
        case 404:
                logging.info('ERROR: CALLSIGN VALIDATION FAILED, NOT IN POTA DATABASE')
                return "ERROR: UNABLE TO SPOT: CALLSIGN NOT IN POTA DATABASE"
        case _:
            logging.info('ERROR: CALLSIGN VALIDATION FAILED, PNP CALLSIGN DATABASE UNAVAILABLE')
            return "ERROR: UNABLE TO SPOT: PNP CALLSIGN DATABASE UNAVAILABLE"

def validatemessage(message):
    logging.info('Validating Message ' + message)
    spotinfo = message.split()
    logging.debug(spotinfo)
    #Check we have the right number of strings
    if len(spotinfo) > 4:
        logging.info("Valid Spot Message Length")
    else:
        if message.split('.') > 1:
            logging.info('ERROR: VALIDATION FAILED: USER USING DOTS NOT SPACES')
            return "INVALID SPOT - PLEASE USE SPACES NOT DOTS"
        else:
            logging.info('ERROR: VALIDATION FAILED: INVALID SPOT MESSAGE')
            return "INVALID SPOT - FORMAT: \"! <Target> <Ref> <Freq> <Mode> <Comment>\""
    #Check we have a valid frequency - This could do with some work to verify within HAM bands      
    if isfloat(spotinfo[3]):
        logging.info("Valid Frequency " + spotinfo[3])
    else:
        logging.info('ERROR: VALIDATION FAILED: INVALID FREQUENCY')
        return "ERROR: INVALID FREQUENCY - MUST BE DECIMAL"
    #Check to see if the modes are within the expected modes
    if spotinfo[4] in ["SSB", "CW", "AM", "FM", "DATA", "PSK", "RTTY"]:
        logging.info('Valid Mode ' + spotinfo[4])
    elif spotinfo[4] in ["FT8"] and spotinfo[1] == "POTA":
        logging.info('Valid mode ' + spotinfo[4] + ' for POTA')
    else:
        logging.info('ERROR: VALIDATION FAILED: INVALID MODE')
        return "ERROR: INVALID MODE - MUST BE SSB|CW|AM|FM|DATA"
    logging.info('Valid Message')
    return True

def sendpnpspot(actclass, actcallsign, actsite, actmode, actfreq, actcomment):
    spotpayload = {"actClass": actclass,"actCallsign": actcallsign,"actSite": actsite,"mode":actmode,"freq":actfreq,"comments": actcomment,"userID": PNPUSERID,"APIKey": PNPAPIKEY}
    logging.info("Sending " + json.dumps(spotpayload))
    if "APTEST" not in actcomment:
        debug = False
        spot = requests.post(PNPURL + "/SPOT", json=spotpayload, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "content-type" : "application/json"})
    else:
        debug = True
        spot = requests.post(PNPURL + "/SPOT/DEBUG", json=spotpayload, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "content-type" : "application/json"})
    if spot.status_code == 200:
        if 'Success' in spot.text:
            if debug:
                logging.info('PNP DEBUG SPOT SUCCESSFUL:')
                logging.debug(spot.text)
                return "SUCCESSFULLY TEST SPOTTED FOR " + actsite + " TO PNP. NO SPOT POSTED"
            else:    
                logging.info('PNP SPOT SUCCESSFUL:')
                logging.debug(spot.text)
                return "SUCCESSFULLY SPOTTED FOR " + actsite + " TO PNP"
        else:
            logging.info('ERROR: UNABLE TO POST SPOT FOR ' + actsite + ' - FAILURE RESPONSE FROM PNP SPOT SUBMISSION')
            return "ERROR: UNABLE TO POST SPOT FOR " + actsite + " TO PNP"
    else:
        logging.info('ERROR: UNABLE TO POST SPOT FOR  ' + actsite + ' - PNP SPOT URL NOT AVAILABLE')
        return "ERROR: UNABLE TO POST SPOT FOR " + actsite + "  TO PNP"

def sendpotaspot(actcallsign, actsite, actmode, actfreq, actcomment):
    spotpayload = {"activator": actcallsign, "spotter": actcallsign, "frequency": str(float(actfreq) * 1000), "reference": actsite, "mode": actmode, "source": "APSPOT-APRS", "comments": actcomment }
    logging.info("Sending " + json.dumps(spotpayload))
    if "APTEST" not in actcomment:
        debug = False
        spot = requests.post(POTAURL + "/spot", json=spotpayload)
    else:
        debug = True
        spot = requests.post(DEVPOTAURL + "/spot", json=spotpayload)
    if spot.status_code == 200:
        if actcallsign in spot.text:
            if debug:
                logging.info('POTA DEV SPOT SUCCESSFUL:')
                logging.debug(spot.text)
                return "SUCCESSFULLY TEST SPOTTED FOR " + actsite + " TO dev.pota.app"
            else:    
                logging.info('POTA SPOT SUCCESSFUL:')
                logging.debug(spot.text)
                return "SUCCESSFULLY SPOTTED FOR " + actsite + " TO pota.app"
        else:
            logging.info('ERROR: UNABLE TO POST SPOT FOR ' + actsite + ' - FAILURE RESPONSE FROM pota.app SPOT SUBMISSION')
            return "ERROR: UNABLE TO POST SPOT FOR " + actsite + " TO pota.app"
    else:
        logging.info('ERROR: UNABLE TO POST SPOT FOR  ' + actsite + ' - pota.app SPOT URL NOT AVAILABLE')
        return "ERROR: UNABLE TO POST SPOT FOR " + actsite + "  TO pota.app"

def processsota_sotawatch(spotinfo, fromcallsign):
    # The SOTA API is pretty dumb, so we can't really do a validation here so we'll just throw the spot in and hope for the best
    spotpayload = { "userID": SOTAUSER ,"associationCode": spotinfo[2].split('/')[0], "summitCode": spotinfo[2].split('/')[1], "activatorCallsign": fromcallsign, "frequency": spotinfo[3], "mode": spotinfo[4].lower(), "comments": getcomment(spotinfo[5])}
    logging.info("Sending " + json.dumps(spotpayload))
    spot = requests.post(SOTAURL + 'spots', json=spotpayload, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "content-type" : "application/json"})
    if spot.status_code == 200:
        logging.info('SOTAWATCH SPOT SUCCESSFUL:')
        logging.debug(spot.text)
        return "SUCCESSFULLY SPOTTED FOR " + spotinfo[2] + " TO SOTAWATCH"
    else:
        logging.info('ERROR: UNABLE TO POST SPOT FOR ' + spotinfo[2] + ' - FAILURE RESPONSE FROM SOTAWATCH SPOT SUBMISSION')
        return "ERROR: UNABLE TO POST SPOT FOR " + spotinfo[2] + " TO SOTAWATCH"

def processpota_pnp(spotinfo, fromcallsign):
    callcheck = validatecall_pnp(fromcallsign)
    if callcheck:
        logging.info('Got POTA Spot, validating Park')
        potaparks=requests.get(PNPURL + '/SITES/POTA/', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if potaparks.status_code == 200:
            logging.info('Got response from PNP server for POTA Parks')
            if spotinfo[2] in potaparks.text:
                logging.info('Park is in DB, SPOT is VALID')
                return sendpnpspot("POTA", fromcallsign, spotinfo[2], spotinfo[4], spotinfo[3], getcomment(spotinfo))
            else:
                logging.info('ERROR: UNABLE TO POST SPOT - PARK NOT IN PNP DATABASE')
                return "ERROR: PARK NOT IN PNP DATABASE"
        else:
            logging.info('ERROR: UNABLE TO POST SPOT - PNP PARK DATABASE NOT AVAILABLE')
            return "ERROR: PNP PARK DATABASE NOT AVAILABLE"
    else:
        return callcheck

def processpota_potaapp(spotinfo, fromcallsign):
    callcheck = validatecall_pota(fromcallsign)
    if callcheck:
        logging.info('Got POTA Spot, validating Park')
        if 'K-TEST' not in spotinfo[2]:
            parkcheck=requests.get(POTAURL + '/park/' + spotinfo[2], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if parkcheck.status_code == 200:
                logging.info('Got response from PNP server for POTA Parks')
                if '"active": 1' in parkcheck.text:
                    logging.info('Park is in DB, SPOT is VALID')
                else:
                    logging.info('ERROR: UNABLE TO POST SPOT - PARK NOT ACTIVE IN POTA DATABASE')
                    return "ERROR: PARK NOT IN POTA DATABASE"
            else:
                logging.info('ERROR: UNABLE TO POST SPOT - POTA PARK DATABASE NOT AVAILABLE')
                return "ERROR: POTA PARK DATABASE NOT AVAILABLE"
        return sendpotaspot(fromcallsign, spotinfo[2], spotinfo[4], spotinfo[3], getcomment(spotinfo))
    else:
        return callcheck

def processsiota_pnp(spotinfo, fromcallsign):
    callcheck = validatecall_pnp(fromcallsign)
    if callcheck:
        logging.info('Got SiOTA Spot, validating Silo')
        silos=requests.get(PNPURL + '/SITES/SIOTA/', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if silos.status_code == 200:
            logging.info('Got response from PNP server for silo')
            if spotinfo[2] in silos.text:
                logging.info('Silo is in DB, SPOT is VALID')
                return sendpnpspot("SIOTA", fromcallsign, spotinfo[2], spotinfo[4], spotinfo[3], getcomment(spotinfo))
            else:
                logging.info('ERROR: UNABLE TO POST SPOT - SILO NOT IN PNP DATABASE')
                return "ERROR: SILO NOT IN PNP DATABASE"
        else:
            logging.info('ERROR: UNABLE TO POST SPOT - PNP SILO DATABASE NOT AVAILABLE')
            return "ERROR: PNP SILO DATABASE NOT AVAILABLE"
    else:
        return callcheck

def processsota_pnp(spotinfo, fromcallsign):
    callcheck = validatecall_pnp(fromcallsign)
    if callcheck:
        logging.info('Got SOTA Spot, validating peak')
        summit=requests.get(PNPURL + '/SUMMIT/' + spotinfo[2], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if summit.status_code == 200:
            logging.info('Got response from PNP server for summit')
            if spotinfo[2] in summit.text.replace('\\', ''):
                logging.info('Summit in database, is it active?')
                if '"Status":"1"' in summit.text: 
                    logging.info('Summit is active, SPOT is VALID')
                    return sendpnpspot("SOTA", fromcallsign, spotinfo[2], spotinfo[4], spotinfo[3], getcomment(spotinfo))
                else:
                    logging.info('ERROR: UNABLE TO POST SPOT - SUMMIT NOT ACTIVE IN PNP DATABASE')
                    return "ERROR: SUMMIT NOT ACTIVE IN PNP DATABASE"
            else:
                logging.info('ERROR: UNABLE TO POST SPOT - SUMMIT NOT IN PNP DATABASE')
                return "ERROR: SUMMIT NOT IN PNP DATABASE"
        else:
            logging.info('ERROR: UNABLE TO POST SPOT - PNP SUMMIT DATABASE NOT AVAILABLE')
            return "ERROR: PNP SUMMIT DATABASE NOT AVAILABLE"
    else:
        return callcheck

def processwwff_pnp(spotinfo, fromcallsign):
    logging.info('Got PNP Spot. Check user is in DB')
    callcheck = validatecall_pnp(fromcallsign)
    if callcheck:
        logging.info('Got WWFF Spot, validating park')
        park=requests.get(PNPURL + '/PARK/WWFF/' + spotinfo[2], headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if park.status_code == 200:
            logging.info('Got response from PNP server for parks')
            if spotinfo[2] in park.text:
                logging.info('Park in database, is it active?')
                if '"Status":"active"' in park.text:
                    logging.info('Park is active, SPOT IS VALID')
                    logging.info('Building Message')
                    return sendpnpspot("WWFF", fromcallsign, spotinfo[2], spotinfo[4], spotinfo[3], getcomment(spotinfo))
                else:
                    logging.info('ERROR: UNABLE TO POST SPOT - PARK NOT ACTIVE IN PNP DATABASE')                                    
                    return "ERROR: PARK NOT ACTIVE IN PNP DATABASE"
            else:
                logging.info('ERROR: UNABLE TO POST SPOT - PARK NOT IN PNP DATABASE')
                return "ERROR: PARK NOT IN PNP DATABASE"
        else:
            logging.info('ERROR: UNABLE TO POST SPOT - PNP SUMMIT DATABASE NOT AVAILABLE')
            return "ERROR: PNP PARKS DATABASE NOT AVAILABLE"
    else:
        return callcheck

def processpot(message, fromcallsign):
    global cache
    if message not in cache.get(hash(fromcallsign + message), ""):
        cache[hash(fromcallsign + message)] = message
        spotinfo = message.split()
        friendlycallsign = fromcallsign.split('-')[0]
        logging.info('Determining Class')
        match spotinfo[1]:
            case 'SOTA':
                sendmessage(processsota_pnp(spotinfo, friendlycallsign), fromcallsign)
            case 'WWFF':
                sendmessage(processwwff_pnp(spotinfo, friendlycallsign), fromcallsign)
            case 'SIOTA':
                sendmessage(processsiota_pnp(spotinfo, friendlycallsign), fromcallsign)
            case 'POTA':
                if 'VK' in message.split()[2]:
                    sendmessage(processpota_pnp(spotinfo, friendlycallsign), fromcallsign)
                sendmessage(processpota_potaapp(spotinfo, friendlycallsign), fromcallsign)
            case _:
                logging.info('ERROR: NO SUPPORT FOR ' + spotinfo[1] + ' YET. CHECK WITH VK2MES FOR UPDATES')
                sendmessage('ERROR: NO SUPPORT FOR ' + spotinfo[1] + ' YET. CHECK WITH VK2MES FOR UPDATES', fromcallsign)
    else:
        logging.info('ERROR: Message ' + message + ' has already been seen in the last 48 hours')
        sendmessage('ERROR: Duplicate message detected', fromcallsign)

def sendspots(message, fromcallsign):
    request = message.split()
    try:
        match request[1]:
            case 'SOTA':
                #We can just grab the SOTA spots of PNP as they're all mirrored there anyway.
                logging.info('Got a request for SOTA spots, getting ALL Spots from PNP')
                spots = requests.get(PNPURL + '/ALL', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                logging.debug(str(spots.text))
                logging.info('Got SPOTS now need to process just SOTA spots')
                sotaspots = [x for x in json.loads(spots.text) if x['actClass'] == 'SOTA']
                logging.debug(str(sotaspots))
                if spots.status_code == 200:
                    logging.info('Got valid response from PNP, now to compile and send response')
                    if '[]' in spots.text:
                        now = datetime.now()
                        sendmessage('No current SOTA spots in parksnpeaks.org' + now.strftime("%Y%m%d%H%M"), fromcallsign)
                    else:
                        for index, spot in zip(range(3), sotaspots):
                            sendmessage('SPOT ' + str(index) + ': ' + spot['actCallsign'] + ' | ' + spot['actSiteID'] + ' | ' + spot['actFreq'] + ' | ' + spot['actMode'], fromcallsign)
                else:
                    logging.info('ERROR: No Response from PNP Server for SOTA Spots')
                    sendmessage('ERROR: No Response from PNP Server for SOTA Spots', fromcallsign)
            case 'WWFF':
                logging.info('Got a request for WWFF spots, getting WWFF Spots from PNP')
                spots = requests.get(PNPURL + '/WWFF', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                logging.debug(spots.text)
                if spots.status_code == 200:
                    logging.info('Got valid response from PNP, now to compile and send response')
                    if '[]' in spots.text:
                        sendmessage('No current WWFF spots in parksnpeaks.org', fromcallsign)
                    else:
                        for index, spot in zip(range(3), json.loads(spots.text)):
                            sendmessage('SPOT ' + str(index) + ': ' + spot['actCallsign'] + ' | ' + spot['WWFFid'] + ' | ' + spot['actFreq'] + ' | ' + spot['actMode'], fromcallsign)
                else:
                    sendmessage('ERROR: No Response from PNP Server for WWFF Spots', fromcallsign)
            case 'SIOTA':
                sendmessage("SIOTA SPOTS NOT IMPLEMENTED", fromcallsign)
            case 'POTA':
                logging.info('Got a request for POTA spots, getting spots from POTA API')
                spots = requests.get(POTAURL + '/spot/activator', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                logging.debug(spots.text)
                if spots.status_code == 200:
                    potaspots = json.loads(spots.text)
                    logging.debug(spots)
                    potaspots.sort(key=extract_potaid, reverse=True)
                    logging.debug(potaspots)
                    for index, spot in zip(range(3), potaspots):
                        sendmessage('SPOT ' + str(index) + ': ' + spot['activator'] + ' | ' + spot['reference'] + ' | ' + spot['frequency'] + ' | ' + spot['mode'], fromcallsign)
                else:
                    sendmessage("ERROR: No response from POTA server", fromcallsign)
            case _:
                sendmessage('SPOTS REQUEST NOT SUPPORTED FOR ' + request[1:], fromcallsign)
    except Exception as e:
        logging.error(e)
        sendmessage('ERROR: MUST SPECIFY A SPOT TYPE: eg WWFF, SOTA, SIOTA, POTA', fromcallsign)

def incomingMessage(packet):
    message = aprslib.parse(packet)
    logging.info('Got message from APRS ' + str(message))
    if (message.get('message_text')):
        logging.info('We have a message so send an ack')
        if message.get('msgNo'):
            sendack(message['from'], message['msgNo'])
            time.sleep(0.5)
        messagetext = message['message_text'].upper()
        if messagetext.startswith("!"):    
            logging.info('Now we need to see if we got a valid SPOT message')
            messagecheck = validatemessage(messagetext)
            if messagecheck == True:
                logging.info('Got a valid SPOT message so process the message')
                processpot(messagetext, message['from'])
            else:
                logging.info('ERROR: Invalid spot message, send result of message validation check to user')
                sendmessage(messagecheck, message['from'])
        elif messagetext.startswith('SPOTS'):
            logging.info('Got a request for ' + messagetext)
            sendspots(message['message_text'].upper(), message['from'])
        else:
            logging.info('Got an invalid request, sending usage information')
            sendusage(message['message_text'].upper(), message['from'])
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