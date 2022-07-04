To Build/Push Container:

docker build -f DockerfileAPSPOT -t 276800331103.dkr.ecr.ap-southeast-2.amazonaws.com/apspot:stable .
docker push 276800331103.dkr.ecr.ap-southeast-2.amazonaws.com/apspot:stable

To update Fargate:

aws ecs update-service --cluster APSPOTCluster --desired-count 1 --service APSPOT --force-new-deployment

To update ECR Cloudformation:

aws cloudformation deploy --template-file aws-ecr.yml --stack-name ECR-APSPOT

To update APSPOT Cloudformaton:

aws cloudformation deploy --template-file aws-fargate.yml --stack-name FARGATE-APSPOT --capabilities CAPABILITY_NAMED_IAM --parameter-overrides PNPAPIKEY=<pnpapikey> PASSCODE=<passcode> CALLSIGN=<callsign>