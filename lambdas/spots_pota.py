import logging
import requests
import json
import os

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

pota_api_url = os.environ['pota_api_url']

def extract_potaid(json):
    try:
        return int(json['spotId'])
    except KeyError:
        return 0

def lambda_handler(event, context):
    spots = []
    numSpots = event["queryStringParameters"]["numSpots"]
    mode = event["queryStringParameters"].get("mode", "ALL")
    logging.info('Got a request for POTA spots, getting spots from POTA API')
    apiresponse = requests.get(pota_api_url + '/spot/activator', headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    logging.debug(apiresponse)
    if '[]' in apiresponse.text or apiresponse.status_code != 200:
        spots.append('No current POTA spots in pota.app')
    else:
        potaspots = json.loads(apiresponse.text)
        if mode in ["CW","FT8","SSB","DATA"]:
            filteredspots = [x for x in potaspots if x['mode'] == mode]
            potaspots = filteredspots
            if len(filteredspots) == 0:
                spots.append("No current " + mode + " POTA spots in pota.app")
        logging.debug(potaspots)
        potaspots.sort(key=extract_potaid, reverse=True)
        logging.debug(potaspots)
        for index, spot in zip(range(int(numSpots)), potaspots):
            spots.append('SPOT ' + str(index + 1) + ': ' + spot['activator'] + ' | ' + spot['reference'] + ' | ' + spot['frequency'] + ' | ' + spot['mode'])
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