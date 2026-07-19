import logging
import requests
import json
import os
import boto3
import time
import urllib.parse
from datetime import datetime

APSPOTAPIURL = os.getenv('APSPOTAPIURL')
messageLimit = 5

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def sendmessage(message, destination, awsNumber):
    snsclient = boto3.client('sns')
    #print('Sending Message: ' + message)
    #print('To: ' + destination)
    #print('From: ' + awsNumber)
    snsclient.publish(PhoneNumber=destination, Message=message)
    #snsclient.publish(PhoneNumber=destination, Message=message, MessageAttributes={'AWS.MM.SMS.OriginationNumber': {'DataType': 'String', 'StringValue': awsNumber}})

def processmessage(action, message, activator=""):
    print("Detemine Message Type")
    print("Got a " + action + " message")
    response = []
    if action == "spot":
        print("Preparing spot URL")
        url = APSPOTAPIURL + '/processmessage?action=spot&activator=' + activator + '&message=' + urllib.parse.quote_plus(message)
        print(url)
    else:
        print("Preparing " + action + " URL")
        url = APSPOTAPIURL + '/processmessage?action=' + action + '&message=' + urllib.parse.quote_plus(message)
        print(url)
    apiresponse = requests.get(str(url), timeout=10)
    #print(apiresponse)
    if apiresponse.status_code == 200:
        #print(apiresponse.text)
        for result in json.loads(apiresponse.text)['response']:
            response.append(str(result))
    else:
        response.append("ERROR CONNECTING TO APSPOT API")
    return response

def lambda_handler(event, context):
    
    #print(event['Records'][0]['Sns']['Message'])
    message = json.loads(event['Records'][0]['Sns']['Message'])
    messagetext = message['messageBody'].upper()
    messagefrom = message['originationNumber']
    awsNumber = message['destinationNumber']
    print('Message from: ' + messagefrom)
    print('Incoming number: ' + awsNumber)
    print('Message Subject: ' + messagetext)

    if 'INREACHLINK' in messagetext:
        messagetext = messagetext.split('INREACHLINK')[0] + ' [InReach]'
    else:
        messagetext = messagetext + ' [SMS]'

    if messagetext.startswith("!"):
        response = processmessage("spot", ' '.join(messagetext.split()[1:]), messagetext.split()[0][1:])
    elif messagetext.startswith('SPOTS'):
        response = processmessage("spots", messagetext[6:])
        if len(response) > messageLimit:
            del response[messageLimit:]
    elif messagetext.startswith('?'):
        response = processmessage("search", messagetext[2:])
        if len(response) > messageLimit:
            del response[messageLimit:]
    else:
        print('Sending usage information')
        response = processmessage("usage", messagetext)

    for reply in response:
        print("Sending Message: " + reply + " to: " + messagefrom + " from: " + awsNumber)
        sendmessage(reply, messagefrom, awsNumber)