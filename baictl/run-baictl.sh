# !/bin/bash
set -ex

# TODO: Ask which credentials should be used
export AWS_PROFILE=mxnet-ci-dev1

# Login to ECR
# TODO: --password-stdin for security purposes
set +x
$(aws ecr get-login --no-include-email --region us-west-2)
set -x

# Build Docker image of baictl
docker build -t benchmark-ai/aws-baictl-baictl-ecs .

# Deploy/Update CloudFormation stack
aws cloudformation deploy --stack-name baictl-ecs --template-file cf-baictl-ecs.yml --capabilities "CAPABILITY_IAM" --no-fail-on-empty-changeset

# TODO: Extract deployment-specified values https://stackoverflow.com/questions/41628487/getting-outputs-from-aws-cloudformation-describe-stacks
aws cloudformation describe-stacks --stack-name baictl-ecs

# Push Docker image to ECR
# TODO: Retrieve these values dynamically
docker tag benchmark-ai/aws-baictl-baictl-ecs:latest 094741945095.dkr.ecr.us-west-2.amazonaws.com/benchmark-ai/aws-baictl-baictl-ecs:latest
docker push 094741945095.dkr.ecr.us-west-2.amazonaws.com/benchmark-ai/aws-baictl-baictl-ecs:latest

# Create run-once task
# TODO: Retrieve these values dynamically
aws ecs run-task --cluster baictl-ecs-cluster --launch-type FARGATE --task-definition arn:aws:ecs:us-west-2:094741945095:task-definition/baictl:3 --network-configuration '{"awsvpcConfiguration":{"subnets":["subnet-0a6f397572fca14ab","subnet-032ea0be3d6f34b65"],"securityGroups":["sg-0dd8c65166734f4fd"],"assignPublicIp":"ENABLED"}}'
# Stream logs ?

# TODO: Ask whether CloudFormation stack should be destroyed again
