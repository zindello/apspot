import logging
import requests
import json
import os
import boto3
import time
import urllib.parse
from datetime import datetime

APSPOTAPIURL = os.getenv('APSPOTAPIURL')

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def sendmessage(message, destination, awsNumber:
    snsclient = boto3.client('sns')
    snsclient.publish(PhoneNumber=destination, Message=message, MessageAttributes={'AWS.MM.SMS.OriginationNumber': {'DataType': 'String', 'StringValue': awsNumber}})

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
    apiresponse = requests.get(str(url))
    logging.debug(apiresponse)
    if apiresponse.status_code == 200:
        logging.debug(apiresponse.text)
        for result in json.loads(apiresponse.text)['response']:
            response.append(result)
    else:
        response.append("ERROR CONNECTING TO APSPOT API")
    return response

def lambda_handler(event, context):
    
    print(event['Records'][0]['Sns']['Message'])
    message = json.loads(event['Records'][0]['Sns']['Message'])
    messagetext = message['messageBody'].upper()
    messagefrom = message['originationNumber']
    awsNumber = message['destinationNumber']

    if messagetext.startswith("!"):
        response = processmessage("spot", messagetext.split()[1:], messagetext.split()[0][1:])
    elif messagetext.startswith('SPOTS'):
        response = processmessage("spots", messagetext.split()[1:])
    elif messagetext.startswith('?'):
        response = processmessage("search", messagetext.split()[1:])
    else:
        logging.info('Sending usage information')
        response = sendusage("usage", messagetext.split()[1:])

    for reply in response:
        sendmessage(reply, messagefrom, awsNumber)


