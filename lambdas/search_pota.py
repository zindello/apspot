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


def lambda_handler(event, context):
    searchResponse = []
    search=event["queryStringParameters"]["search"]
    
    searchresult=requests.get(pota_api_url + '/lookup?search=' + search)
    if searchresult.status_code == 200:
        for index, park in zip(range(5), json.loads(searchresult.text)):
            searchResponse.append("Result " + str(index + 1) + ": " + park['display'])

    if len(searchResponse) == 0:
        searchResponse.append('Not found ' + search + ' try a single word instead')

    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": 'Content-Type',
            "Access-Control-Allow-Origin": '*',
            "Access-Control-Allow-Methods": 'OPTIONS,GET'
        },
        "body": "{ \"response\":" + json.dumps(searchResponse) + " }"
    }
    return response