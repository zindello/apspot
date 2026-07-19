import boto3

snsclient = boto3.client('sns')
print(snsclient.publish(PhoneNumber = '+61416039082', Message='This is a test message', MessageAttributes={'AWS.MM.SMS.OriginationNumber': {'DataType': 'String', 'StringValue': '+18678772605'}}))