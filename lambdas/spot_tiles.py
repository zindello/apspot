import logging
import requests
import json
import os

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

tiles_api_url = os.environ['tiles_api_url']
tiles_api_key = os.environ['tiles_api_key']


def sendtilesspot(actcallsign, actref, actmode, actfreq, actcomment):
    spotpayload = {
        "call_sign": actcallsign,
        "ref": actref,
        "frequency": float(actfreq),
        "mode": actmode,
        "comment": actcomment
    }
    logging.info("Sending " + json.dumps(spotpayload))
    if "APTEST" in actcomment.upper():
        logging.info('APTEST in comment, not posting spot to tilesontheair.com')
        return "TEST SPOT FOR " + actref + " NOT POSTED TO tilesontheair.com"
    headers = {"x-api-key": tiles_api_key, "Content-Type": "application/json"}
    spot = requests.post(tiles_api_url, json=spotpayload, headers=headers, timeout=10)
    if spot.status_code == 201:
        logging.info('TILES SPOT SUCCESSFUL:')
        logging.debug(spot.text)
        return "SUCCESSFULLY SPOTTED FOR " + actref + " TO tilesontheair.com"
    else:
        # Facundo returns 401/422 with a reason we can pass back as an ACK
        reason = ""
        try:
            reason = json.loads(spot.text).get("reason", "") or json.loads(spot.text).get("message", "")
        except Exception:
            reason = spot.text
        logging.info('ERRTILES: UNABLE TO POST SPOT FOR ' + actref + ' - ' + str(spot.status_code) + ' ' + str(reason))
        return "ERRTILES: UNABLE TO POST SPOT FOR " + actref + " TO tilesontheair.com" + ((" - " + str(reason)) if reason else "")


def lambda_handler(event, context):
    callsign = event["queryStringParameters"]["callsign"]
    ref = event["queryStringParameters"]["ref"]
    freq = event["queryStringParameters"]["freq"]
    mode = event["queryStringParameters"]["mode"]
    comment = event["queryStringParameters"]["comment"]

    spotResponse = sendtilesspot(callsign, ref, mode, freq, comment)

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
