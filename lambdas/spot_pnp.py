import logging
import requests
import json
import os

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

pnp_api_url = os.environ['pnp_api_url']
pnp_api_user_id = os.environ['pnp_api_user_id']
pnp_api_user_key = os.environ['pnp_api_user_key']

spotResponse = []

def validatecall_pnp(callsign):
    print('Getting callsign database from PNP')
    callsigns=requests.get(pnp_api_url + '/callsign/', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if callsigns.status_code == 200:
        if callsign in callsigns.text:
            print('CALLSIGN VALIDATED')
            return True
        else:
            print('ERRPNP: CALLSIGN VALIDATION FAILED, NOT IN PNP DATABASE')
            return False
    else:
        print('ERRPNP: CALLSIGN VALIDATION FAILED, PNP CALLSIGN DATABASE UNAVAILABLE')
        return False

def validatesilo_pnp(ref):
    silos=requests.get(pnp_api_url + '/SITES/SIOTA/', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if silos.status_code == 200:
        print('Got response from PNP server for silo')
        if ref in silos.text:
            print('Silo is in DB, SPOT is VALID')
            return True
        else:
            print('ERRPNP: UNABLE TO POST SPOT - SILO NOT IN PNP DATABASE')
            return False
    else:
        print('ERRPNP: UNABLE TO POST SPOT - PNP SILO DATABASE NOT AVAILABLE')
        return False

def validatesummit_pnp(ref):
    summit=requests.get(pnp_api_url + '/SUMMIT/' + ref, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if summit.status_code == 200:
        print('Got response from PNP server for summit')
        if ref in summit.text.replace('\\', ''):
            print('Summit in database, is it active?')
            if '"Status":"1"' in summit.text: 
                print('Summit is active, SPOT is VALID')
                return True
            else:
                print('ERRPNP: UNABLE TO POST SPOT - SUMMIT NOT ACTIVE IN PNP DATABASE')
                return False
        else:
            print('ERRPNP: UNABLE TO POST SPOT - SUMMIT NOT IN PNP DATABASE')
            return False
    else:
        print('ERRPNP: UNABLE TO POST SPOT - PNP SUMMIT DATABASE NOT AVAILABLE')
        return False

def validatewwff_pnp(ref):
    park=requests.get(pnp_api_url + '/PARK/WWFF/' + ref, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if park.status_code == 200:
        print('Got response from PNP server for parks')
        if ref in park.text:
            print('Park in database, is it active?')
            if '"Status":"active"' in park.text:
                print('Park is active, SPOT IS VALID')
                return True
            else:
                print('ERRPNP: UNABLE TO POST SPOT - PARK NOT ACTIVE IN PNP DATABASE')                                    
                return False
        else:
            print('ERRPNP: UNABLE TO POST SPOT - PARK NOT IN PNP DATABASE')
            return False
    else:
        print('ERRPNP: UNABLE TO POST SPOT - PNP SUMMIT DATABASE NOT AVAILABLE')
        return False

def validatepota_pnp(ref):
    print('Got POTA Spot, validating Park')
    potaparks=requests.get(pnp_api_url + '/SITES/POTA/', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if potaparks.status_code == 200:
        print('Got response from PNP server for POTA Parks')
        if ref in potaparks.text:
            print('Park is in DB, SPOT is VALID')
            return True
        else:
            print('ERRPNP: UNABLE TO POST SPOT - PARK NOT IN PNP DATABASE')
            return False
    else:
        print('ERRPNP: UNABLE TO POST SPOT - PNP PARK DATABASE NOT AVAILABLE')
        return False

def sendpnpspot(actclass, actcallsign, actsite, actmode, actfreq, actcomment):
    spotpayload = {"actClass": actclass,"actCallsign": actcallsign,"actSite": actsite,"mode":actmode,"freq":actfreq,"comments": actcomment,"userID": pnp_api_user_id,"APIKey": pnp_api_user_key}
    print("Sending " + json.dumps(spotpayload))
    if "APTEST" not in actcomment:
        debug = False
        spot = requests.post(pnp_api_url + "/SPOT", json=spotpayload, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "content-type" : "application/json"})
    else:
        debug = True
        spot = requests.post(pnp_api_url + "/SPOT/DEBUG", json=spotpayload, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "content-type" : "application/json"})
    if spot.status_code == 200:
        if 'Success' in spot.text:
            if debug:
                print('PNP DEBUG SPOT SUCCESSFUL:')
                print(spot.text)
                return "SUCCESSFULLY TEST SPOTTED FOR " + actsite + " TO PNP. NO SPOT POSTED"
            else:    
                print('PNP SPOT SUCCESSFUL:')
                print(spot.text)
                return "SUCCESSFULLY SPOTTED FOR " + actsite + " TO PNP"
        else:
            print('ERRPNP: UNABLE TO POST SPOT FOR ' + actsite + ' - FAILURE RESPONSE FROM PNP SPOT SUBMISSION')
            return "ERRPNP: UNABLE TO POST SPOT FOR " + actsite + " TO PNP"
    else:
        print('ERRPNP: UNABLE TO POST SPOT FOR  ' + actsite + ' - PNP SPOT URL NOT AVAILABLE')
        return "ERRPNP: UNABLE TO POST SPOT FOR " + actsite + "  TO PNP"

def lambda_handler(event, context):
    callsign=event["queryStringParameters"]["callsign"]
    ref=event["queryStringParameters"]["ref"]
    freq=event["queryStringParameters"]["freq"]
    mode=event["queryStringParameters"]["mode"]
    comment=event["queryStringParameters"]["comment"]
    pnpSpotType=event["queryStringParameters"]["pnpSpotType"]

    callcheck = validatecall_pnp(callsign)

    if pnpSpotType == "WWFF":
        refcheck = validatewwff_pnp(ref)
    elif pnpSpotType == "SOTA":
        refcheck = validatesummit_pnp(ref)
    elif pnpSpotType == "SIOTA":
        refcheck = validatesilo_pnp(ref)
    elif pnpSpotType == "POTA":
        refcheck = validatepota_pnp(ref)
    else:
        refcheck = False

    if callcheck and refcheck:
        spotResponse = sendpnpspot(pnpSpotType, callsign, ref, mode, freq, comment)
    else:
        spotResponse = "ERRPNP:"
        if callcheck != True:
            spotResponse = spotResponse + " " + callsign + " NOT IN DB"
        if refcheck != True:
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