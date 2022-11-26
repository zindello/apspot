To Build/Push Container:
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 276800331103.dkr.ecr.ap-southeast-2.amazonaws.com
docker build -f DockerfileAPSPOT -t 276800331103.dkr.ecr.ap-southeast-2.amazonaws.com/apspot:stable .
docker push 276800331103.dkr.ecr.ap-southeast-2.amazonaws.com/apspot:stable

To update Fargate:

aws ecs update-service --cluster APSPOTCluster --desired-count 1 --service APSPOT --force-new-deployment

To update ECR Cloudformation:

aws cloudformation deploy --template-file aws-ecr.yml --stack-name ECR-APSPOT

To update APSPOT Cloudformaton:

aws cloudformation deploy --template-file aws-fargate.yml --stack-name FARGATE-APSPOT --capabilities CAPABILITY_NAMED_IAM --parameter-overrides PNPAPIKEY=<pnpapikey> PASSCODE=<passcode> CALLSIGN=<callsign>




APRS Daemon - ECS/Fargate

Monitors APRS-IS for incoming messages and calls API. Handles sending messages back to APRS-IS.


Email Receive/Response - Lambda

Receives an incoming email. Handles sending messages back via email. Maybe restrict to winlink email addresses?


API:

/spot/wwff?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/pota?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/sota?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/siota?callsign=<callsign>&ref=<ref>&freq=<freq>&mode=<mode>(&comment=<comment>)
/spot/{proxy+}
/spots/pota(?numSpots=<integer>)
/spots/wwff(?numSpots=<integer>)
/spots/sota(?numSpots=<integer>)
/spots/siota(?numSpots=<integer>)
/search/wwff?search=<string>
/search/pota?search=<string>
/search/sota?search=<string>
/search/siota?search=<string>