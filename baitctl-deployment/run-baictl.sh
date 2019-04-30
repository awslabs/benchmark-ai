# !/bin/bash
set -ex

# Ask which credentials should be used
export AWS_PROFILE=mxnet-ci-dev1

# Login to ECR
# TODO: This writes credentials to STDOUT. Fix!
$(aws ecr get-login --no-include-email --region us-west-2)

# Build Docker image of baictl
docker build -t benchmark-ai/aws-baictl-baictl-ecs .

# Deploy/Update CloudFormation stack
aws cloudformation deploy --stack-name baictl-ecs --template-file cf-baictl-ecs.yml --capabilities "CAPABILITY_IAM" --no-fail-on-empty-changeset

# Push Docker image to ECR
docker tag benchmark-ai/aws-baictl-baictl-ecs:latest 094741945095.dkr.ecr.us-west-2.amazonaws.com/benchmark-ai/aws-baictl-baictl-ecs:latest
docker push 094741945095.dkr.ecr.us-west-2.amazonaws.com/benchmark-ai/aws-baictl-baictl-ecs:latest

# Create run-once task
aws ecs run-task --cluster baictl-ecs-cluster --launch-type FARGATE --task-definition arn:aws:ecs:us-west-2:094741945095:task-definition/baictl:1 --network-configuration '{"awsvpcConfiguration":{"subnets":["subnet-01f2b8c5ebad849dd","subnet-0fe18726b524db0fd"],"securityGroups":["sg-071cd497121b0e9ad"],"assignPublicIp":"ENABLED"}}'
# Stream logs ?

# Ask whether CloudFormation stack should be destroyed again
