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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ParksNPeaks now runs on the "On The Air" platform. Spot references are
# validated against its /assets endpoint; each PnP spot class maps to one
# asset_type there (see /api/assettypes).
PNP_ASSET_TYPES = {
    "WWFF": "wwff park",
    "SOTA": "summit",
    "POTA": "pota park",
    "SIOTA": "silo",
}

spotResponse = []


def mhz_to_khz(freq):
    # Inbound APRS messages carry MHz; the On The Air API wants kHz.
    try:
        khz = float(freq) * 1000
    except (TypeError, ValueError):
        return freq
    text = '%.1f' % khz
    if text.endswith('.0'):
        text = text[:-2]
    return text


def validateref_pnp(pnpSpotType, ref):
    asset_type = PNP_ASSET_TYPES.get(pnpSpotType)
    if asset_type is None:
        print('ERRPNP: UNKNOWN SPOT TYPE ' + str(pnpSpotType))
        return False
    print('Validating ' + pnpSpotType + ' reference ' + ref + ' against PNP assets')
    # The assets code lookup only matches when '/' is sent as '_'
    # (e.g. SOTA summit VK3/VC-001 is looked up as VK3_VC-001).
    lookup = requests.get(pnp_api_url + '/assets',
                          params={"code": ref.replace('/', '_')},
                          headers=HEADERS)
    if lookup.status_code != 200:
        print('ERRPNP: UNABLE TO POST SPOT - PNP ASSET DATABASE NOT AVAILABLE')
        return False
    try:
        assets = json.loads(lookup.text)
    except ValueError:
        print('ERRPNP: UNABLE TO POST SPOT - UNEXPECTED RESPONSE FROM PNP ASSET DATABASE')
        return False
    matches = [a for a in assets if a.get('asset_type') == asset_type]
    if not matches:
        print('ERRPNP: UNABLE TO POST SPOT - ' + ref + ' NOT IN PNP DATABASE AS ' + pnpSpotType)
        return False
    if not matches[0].get('is_active'):
        print('ERRPNP: UNABLE TO POST SPOT - ' + ref + ' NOT ACTIVE IN PNP DATABASE')
        return False
    print('Reference is in DB and active, SPOT is VALID')
    return True


def sendpnpspot(actclass, actcallsign, actsite, actmode, actfreq, actcomment):
    debug = "APTEST" in actcomment.upper()
    comment = actcomment
    if debug and "DEBUG" not in actcomment.upper():
        # The old /SPOT/DEBUG endpoint is gone; the On The Air API routes any
        # spot whose comment contains the word DEBUG to its test topic instead
        # of the live feed.
        comment = (actcomment + " DEBUG").strip()
    spotpayload = {
        "userID": pnp_api_user_id,
        "APIKey": pnp_api_user_key,
        "activator": actcallsign,
        "spotter": actcallsign,
        "reference": actsite,
        "frequency": mhz_to_khz(actfreq),
        "mode": actmode,
        "comments": comment,
    }
    logpayload = {k: v for k, v in spotpayload.items() if k != "APIKey"}
    print("Sending " + json.dumps(logpayload))
    # Posted as multipart/form-data: the platform's documented example uses
    # curl -F, and newer platform builds 500 on urlencoded bodies.
    spot = requests.post(pnp_api_url + "/spots",
                         files={k: (None, str(v)) for k, v in spotpayload.items()},
                         headers=HEADERS)
    if spot.status_code == 200:
        try:
            result = json.loads(spot.text)
        except ValueError:
            result = {}
        if result.get('success'):
            if debug:
                print('PNP DEBUG SPOT SUCCESSFUL:')
                print(spot.text)
                return "SUCCESSFULLY TEST SPOTTED FOR " + actsite + " TO PNP. NO SPOT POSTED"
            else:
                print('PNP SPOT SUCCESSFUL:')
                print(spot.text)
                return "SUCCESSFULLY SPOTTED FOR " + actsite + " TO PNP"
        else:
            print('ERRPNP: UNABLE TO POST SPOT FOR ' + actsite + ' - FAILURE RESPONSE FROM PNP: ' + str(result.get('message', spot.text)))
            return "ERRPNP: UNABLE TO POST SPOT FOR " + actsite + " TO PNP"
    else:
        print('ERRPNP: UNABLE TO POST SPOT FOR ' + actsite + ' - PNP SPOT URL NOT AVAILABLE')
        return "ERRPNP: UNABLE TO POST SPOT FOR " + actsite + " TO PNP"


def lambda_handler(event, context):
    callsign = event["queryStringParameters"]["callsign"]
    ref = event["queryStringParameters"]["ref"]
    freq = event["queryStringParameters"]["freq"]
    mode = event["queryStringParameters"]["mode"]
    comment = event["queryStringParameters"]["comment"]
    pnpSpotType = event["queryStringParameters"]["pnpSpotType"]

    # The old per-scheme validation endpoints (and the callsign database) no
    # longer exist on the new platform; references are validated against
    # /assets and callsigns are validated server-side on spot submission.
    refcheck = validateref_pnp(pnpSpotType, ref)

    if refcheck:
        spotResponse = sendpnpspot(pnpSpotType, callsign, ref, mode, freq, comment)
    else:
        spotResponse = "ERRPNP: " + ref + " NOT IN DB"

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
