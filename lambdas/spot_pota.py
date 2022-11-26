import logging
import requests
import json
import os

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

pota_api_url = os.environ['pota_api_url']
pota_api_dev_url = os.environ['pota_api_dev_url']



def validatecall_pota(callsign):
    logging.info('Getting callsign database from POTA')
    callsigns=requests.get(pota_api_url + '/stats/user/' + callsign)
    if callsigns.status_code == 200:
        if callsign in callsigns.text:
            logging.info('CALLSIGN VALIDATED')
            return True
    elif callsigns.status_code == 404:
        logging.info('ERRPOTA: CALLSIGN VALIDATION FAILED, NOT IN POTA DATABASE')
        return False
    else:
        logging.info('ERRPOTA: CALLSIGN VALIDATION FAILED, POTA CALLSIGN DATABASE UNAVAILABLE')
        return False

def validatepark_pota(park):
    if park != 'K-TEST':
        parkcheck=requests.get(pota_api_url + '/park/' + park)
        if parkcheck.status_code == 200:
            logging.info('Got response from PNP server for POTA Parks')
            if '"active": 1' in parkcheck.text:
                logging.info('Park is in DB, SPOT is VALID')
                return True
            else:
                logging.info('ERRPOTA: UNABLE TO POST SPOT - PARK NOT ACTIVE IN POTA DATABASE')
                return False
        else:
            logging.info('ERRPOTA: UNABLE TO POST SPOT - POTA PARK DATABASE NOT AVAILABLE')
            return False
    return True

def sendpotaspot(actcallsign, actsite, actmode, actfreq, actcomment):
    spotpayload = {"activator": actcallsign, "spotter": actcallsign, "frequency": str(float(actfreq) * 1000), "reference": actsite, "mode": actmode, "source": "APSPOT-APRS", "comments": actcomment }
    logging.info("Sending " + json.dumps(spotpayload))
    response = []
    if "APTEST" not in actcomment:
        debug = False
        spot = requests.post(pota_api_url + "/spot", json=spotpayload)
    else:
        debug = True
        spot = requests.post(pota_api_dev_url + "/spot", json=spotpayload)
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
            logging.info('ERRPOTA: UNABLE TO POST SPOT FOR ' + actsite + ' - FAILURE RESPONSE FROM pota.app SPOT SUBMISSION')
            return "ERRPOTA: UNABLE TO POST SPOT FOR " + actsite + " TO pota.app"
    else:
        logging.info('ERRPOTA: UNABLE TO POST SPOT FOR  ' + actsite + ' - pota.app SPOT URL NOT AVAILABLE')
        return "ERRPOTA: UNABLE TO POST SPOT FOR " + actsite + "  TO pota.app"
    

def lambda_handler(event, context):
    callsign=event["queryStringParameters"]["callsign"]
    ref=event["queryStringParameters"]["ref"]
    freq=event["queryStringParameters"]["freq"]
    mode=event["queryStringParameters"]["mode"]
    comment=event["queryStringParameters"]["comment"]

    spotResponse = []

    callcheck = validatecall_pota(callsign)
    parkcheck = validatepark_pota(ref)

    if callcheck and parkcheck:
        spotResponse = sendpotaspot(callsign, ref, mode, freq, comment)
    else:
        spotResponse = "ERRPOTA:"
        if callcheck != True:
            spotResponse = spotResponse + " " + callsign + " NOT IN DB"
        if parkcheck != True:
            spotResponse = spotResponse + " " + ref + " NOT IN DB"
        


    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": 'Content-Type',
            "Access-Control-Allow-Origin": '*',
            "Access-Control-Allow-Methods": 'OPTIONS,GET'
        },
        "body": "{ \"response\":\"" + spotResponse + "\" }"

    }
    return response