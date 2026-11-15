import logging
import requests
import json
import os

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

pnp_api_url = os.environ['pnp_api_url']


def lambda_handler(event, context):
    spots = []
    numSpots = event["queryStringParameters"]["numSpots"]
    mode = event["queryStringParameters"].get("mode", "ALL")
    logging.info('Got a request for WWFF spots, getting WWFF Spots from PNP')
    # The dedicated /WWFF feed was removed in the On The Air migration; the
    # legacy-format /ALL feed remains and is filtered by actClass instead.
    apiresponse = requests.get(pnp_api_url + '/ALL', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    logging.debug(apiresponse)
    if '[]' in apiresponse.text or apiresponse.status_code != 200:
        spots.append('No current WWFF spots in parksnpeaks.org')
    else:
        logging.info('Got SPOTS now need to process just WWFF spots')
        wwffspots = [x for x in json.loads(apiresponse.text) if x['actClass'] == 'WWFF']
        if len(wwffspots) == 0:
            spots.append('No current WWFF spots in parksnpeaks.org')
        else:
            if mode in ["SSB", "CW", "AM", "FM", "DATA", "PSK", "RTTY"]:
                filteredspots = [x for x in wwffspots if x['actMode'] == mode]
                wwffspots = filteredspots
                if len(filteredspots) == 0:
                    spots.append("No current " + mode + " WWFF spots in parksnpeaks.org")
            logging.info('Got valid response from PNP, now to compile and send response')
            for index, spot in zip(range(int(numSpots)), wwffspots):
                spots.append('SPOT ' + str(index + 1) + ': ' + spot['actCallsign'] + ' | ' + spot['actSiteID'] + ' | ' + spot['actFreq'] + ' | ' + spot['actMode'])
    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": 'Content-Type',
            "Access-Control-Allow-Origin": '*',
            "Access-Control-Allow-Methods": 'OPTIONS,GET'
        },
        "body": "{ \"response\":" + json.dumps(spots) + "}"
    }
    return response
