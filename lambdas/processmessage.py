import logging
import requests
import json
import os
import urllib.parse

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

pota_api_url = os.environ['pota_api_url']
pota_api_dev_url = os.environ['pota_api_dev_url']

APSPOTAPIURL = os.getenv('APSPOTAPIURL')

USAGESTRING = {
    "USAGE": [
        "APSPOT USAGE INFORMATION - 6 MSGS",
        "TO SPOT SEND: \"! <Target> <Ref> <Freq> <Mode> <Comment>\" WITHOUT QUOTES",
        "TO GET SPOTS SEND: \"SPOTS TARGET\" | REQUESTS ARE CASE INSENSITIVE",
        "VALID TARGETS: SOTA, WWFF, POTA, SIOTA",
        "FOR MORE HELP SEND USAGE <Target> EG:\"USAGE WWFF\"",
        "INCLUDE \"APTEST\" IN COMMENT AND SPOT WILL NOT BE POSTED"
    ],
    "USAGE WWFF": [
        "EXAMPLE: \"! WWFF VKFF-1929 7.144 SSB CQCQ\""
    ],
    "USAGE SOTA": [
        "EXAMPLE: \"! SOTA VK3/VN-030 7.090 SSB QCQ\""
    ],
    "USAGE SIOTA": [
        "EXAMPLE: \"! SIOTA VK-YNE5 7.090 SSB CQCQ\""
    ],
    "USAGE POTA": [
        "EXAMPLE: \"! POTA VK-3024 7.195 SSB CQCQ\""
    ]
}

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

def getcomment(message):
    try:
        return ' '.join(message[4:]) + " [APSPOT]"
    except:
        return "[APSPOT]"

def get_val(myList, idx, default):
    try:
        return myList[idx]
    except IndexError:
        return default

def callapspotapi(action, message, callsign=None):
    response = []
    if action == "spot":
        print('Got a SPOT request for the API, checking destination')
        if message[0] in ["POTA","WWFF","SOTA","SIOTA"]:
            if message[0] == "POTA":
                print('Message destination is POTA, setting up the call to the API to send to pota')
                pota_full_url = APSPOTAPIURL + '/spot/pota' + '?callsign=' + callsign + '&ref=' + urllib.parse.quote_plus(message[1]) + '&freq=' + urllib.parse.quote_plus(message[2]) + '&mode=' + message[3] + '&comment=' + urllib.parse.quote_plus(getcomment(message))
                print(pota_full_url)
                potaspot = requests.get(pota_full_url, timeout=10)
                if potaspot.status_code == 200:
                    print('Got a 200 response from the API, add response message')
                    print(potaspot.text)
                    response.append(json.loads(potaspot.text)['response'])
                else:
                    print('Got a non 200 response from the API, error out')
                    print(potaspot)
                    response.append("Failed posting spot to pota.app")
            if message[0] in ["WWFF","SOTA","SIOTA"] or (message[0] == "POTA" and message[1].startswith('VK')):
                pnp_full_url = APSPOTAPIURL + '/spot/pnp' + '?pnpSpotType=' + message[0] + '&callsign=' + callsign + '&ref=' + urllib.parse.quote_plus(message[1]) + '&freq=' + urllib.parse.quote_plus(message[2]) + '&mode=' + message[3] + '&comment=' + urllib.parse.quote_plus(getcomment(message))
                print(pnp_full_url)
                pnpspot = requests.get(pnp_full_url, timeout=10)
                if pnpspot.status_code == 200:
                    print('Got a 200 response from the API, add response message')
                    response.append(json.loads(pnpspot.text)['response'])
                else:
                    print('Got a non 200 response from the API, error out')
                    response.append("Failed posting spot to parksnpeaks.org")
        else:
            response.append("Target not supported")
    elif action == "spots":
        print(message)
        print(message[0].lower())

        numSpots = 3
        mode = "ALL"   

        secondCommand = get_val(message, 1, "NONE")
        if secondCommand != "NONE":
            try:
                numSpots = int(secondCommand)
                if int(numSpots) > 5: numSpots = 5
            except:
                mode = secondCommand
                thirdCommand = get_val(message, 2, "NONE")
                try:
                    numSpots = int(thirdCommand)
                    if int(numSpots) > 5: numSpots = 5
                except:
                    pass

        spots = requests.get(APSPOTAPIURL + '/spots/' + message[0].lower() + '?numSpots=' + str(numSpots) + '&mode=' + mode, timeout=10)
        if spots.status_code == 200:
            print(json.loads(spots.text)['response'])
            response.extend(json.loads(spots.text)['response'])
        else:
            response.append('Error connecting to APSPOT API')

    elif action == "search":
        if message[0] == "POTA":
            results = requests.get(APSPOTAPIURL + '/search/' + message[0].lower() + '?search=' + str(' '.join(message[1:])), timeout=10)
            if results.status_code == 200:
                response.extend(json.loads(results.text)['response'])
            else:
                response.append('Error connecting to APSPOT API')
        else:
            response.append('Search not supported for ' + message[0])
    return response

def usage(message):
    response = []
    try:
        for usagemessage in USAGESTRING[message]:
            response.append(usagemessage)
    except:
        response.append("ERROR: \"" + message + "\" NOT SUPPORTED")
        response.append("SEND \"USAGE\" FOR MORE INFO")
    return response

def validatemessage(message):
    print('Validating Message')
    logging.debug(message)
    #Check we have the right number of strings
    if len(message) > 4:
        print("Valid Spot Message Length")
    else:
        if message.split('.') > 1:
            print('ERROR: VALIDATION FAILED: USER USING DOTS NOT SPACES')
            return "INVALID SPOT - PLEASE USE SPACES NOT DOTS"
        else:
            print('ERROR: VALIDATION FAILED: INVALID SPOT MESSAGE')
            return "INVALID SPOT - FORMAT: \"! <Target> <Ref> <Freq> <Mode> <Comment>\""
    #Check we have a valid frequency - This could do with some work to verify within HAM bands      
    if isfloat(message[2]):
        print("Valid Frequency " + message[3])
    else:
        print('ERROR: VALIDATION FAILED: INVALID FREQUENCY')
        return "ERROR: INVALID FREQUENCY - MUST BE DECIMAL"
    #Check to see if the modes are within the expected modes
    if message[3] in ["SSB", "CW", "AM", "FM", "DATA", "PSK", "RTTY"]:
        print('Valid Mode ' + message[3])
    elif message[3] in ["FT8"] and message[1] == "POTA":
        print('Valid mode ' + message[3] + ' for POTA')
    else:
        print('ERROR: VALIDATION FAILED: INVALID MODE')
        return "ERROR: INVALID MODE - MUST BE SSB|CW|AM|FM|DATA"
    print('Valid Message')
    return True

def sendspot(message, callsign):
    print('Now we need to see if we got a valid SPOT message')
    message[0] = message[0].upper()
    message[1] = message[1].upper()
    message[3] = message[3].upper()
    messagecheck = validatemessage(message)
    if messagecheck == True:
        print('Got a valid SPOT message so process the message')
        print('Sending spot to API')
        response = callapspotapi("spot", message, callsign)
        print('Got response from API:')
        print(response)
        return response
    else:
        print('ERROR: Invalid spot message, send result of message validation check to user')
        return response

def sendspots(message):
    print('Sending spots request to API')
    response = callapspotapi("spots", message)
    print('Got response from API:')
    print(response)
    return response

def search(message):
    print('Sending search request to API')
    response = callapspotapi("search", message)
    print('Got response from API:')
    print(response)
    print('Sending response over APRS')
    return response

def lambda_handler(event, context):
    action=event["queryStringParameters"]["action"]

    if action == 'spot':
        response = sendspot(urllib.parse.unquote(event["queryStringParameters"]["message"]).split(), event["queryStringParameters"]["activator"].upper())
    elif action == 'spots':
        response = sendspots(urllib.parse.unquote(event["queryStringParameters"]["message"]).split())
    elif action == 'search':
        response = search(urllib.parse.unquote(event["queryStringParameters"]["message"]).split())
    else:
        if urllib.parse.unquote(event["queryStringParameters"]["message"]) == "":
            usagestring = "USAGE"
        else: 
            usagestring = "USAGE " + urllib.parse.unquote(event["queryStringParameters"]["message"].upper())
        response = usage(usagestring)

    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": 'Content-Type',
            "Access-Control-Allow-Origin": '*',
            "Access-Control-Allow-Methods": 'OPTIONS,GET'
        },
        "body": "{ \"response\":" + json.dumps(response) + " }"
    }
    return response