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

def sendmessage(message, destination, source):
    sesclient = boto3.client('ses')
    charset = "UTF-8"
    source = "APSPOT <" + source + ">"
    if destination.split('@')[1] == 'winlink.org':
        subject = '//WL2K/ ' + message[0]
    else:
        subject = message[0]
    body = ""
    if len(message) > 1:
        for line in message:
            body = body + "\r\n" + line
    print('To: ' + destination)
    print('From: ' + source)
    print('Subject: ' + subject)
    print('Body: ' + body)
    sesclient.send_email(
        Destination={
            'ToAddresses': [
                destination.lower()
            ]
        },
        Message={
            'Body': {
                'Text':{
                    #'Charset': charset,
                    'Data': body
                }
            },
            'Subject': {
                'Charset': charset,
                'Data': subject
            }
        },
        Source=source,
        ReplyToAddresses=[
            source
        ],
        ReturnPath=source
    )

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

    #print(json.dumps(event))
    message = json.loads(event['Records'][0]['Sns']['Message'])
    messagefrom = message['mail']['commonHeaders']['from'][0]
    messageto = message['mail']['commonHeaders']['to'][0]
    messagetext = message['mail']['commonHeaders']['subject'].upper()

    print('Message from: ' + messagefrom)
    print('Message: ' + messagetext)

    if messagetext.startswith("!"):
        if messagefrom.split('@')[1] == 'winlink.org':
            response = processmessage("spot", ' '.join(messagetext.split()[1:]) + ' [WL]', messagefrom.split('@')[0].upper())
        else:
            response = ["ERROR: SPOT COMMANDS ONLY ACCPETED FROM Winlink"]
    elif messagetext.startswith('SPOTS'):
        response = ['APSPOT SPOTS ' + messagetext.split()[1] + ' COMMAND RESPONSE']
        messagelist = messagetext.split()
        if not isinstance(messagelist[len(messagelist) - 1], int):
            messagetext = messagetext + ' 10'
        response.extend(processmessage("spots", messagetext[6:]))
    elif messagetext.startswith('?'):
        response = ['APSPOT ? (SEARCH) COMMAND RESPONSE']
        response.extend(processmessage("search", messagetext[2:]))
    else:
        response = ['APSPOT USAGE INFORMATION']
        print('Sending usage information')
        response.extend(processmessage("usage", messagetext))

    sendmessage(response, messagefrom, messageto)
