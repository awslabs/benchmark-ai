#!/usr/bin/env python3

# This script allows to run baictl in a remote fashion by running all commands within an ECS
# cluster. It is designed in an atomic and idemptoent way that allows to interrupt the execution on your local
# computer at any point in time without resisting in data loss or similar non-recoverable states.
# Please don't forget to install the python requirements.txt before running this script.

import boto3
import botocore
import os
import docker
import base64
import logging

DOCKER_IMAGE_TAG = "benchmark-ai/baictl"
CLOUDFORMATION_YAML_PATH = os.path.join(os.path.split(os.path.realpath(__file__))[0], "cfn-baictl-ecs.yml")


def main():
    logging.getLogger().setLevel(logging.DEBUG)

    boto_session = request_aws_credentials()
    docker_cli, docker_registry = login_ecr(boto_session=boto_session)
    docker_tag = build_docker_image(docker_cli=docker_cli, docker_registry=docker_registry)
    cloudformation_output = execute_cloudformation_deployment(
        stack_name="baictl-ecs", boto_session=boto_session, cloudformation_yaml_path=CLOUDFORMATION_YAML_PATH
    )
    publish_docker_image(docker_cli=docker_cli, docker_tag=docker_tag)
    run_ecs_task(boto_session=boto_session, cloudformation_output=cloudformation_output)
    destroy_cloudformation()


def request_aws_credentials():
    # This allows to pick up an AWS_PROFILE and AWS_REGION from the env-var and present it to the user so they only have to press
    # enter instead of having to type it in all the time - just a convenience thingy
    env_aws_profile = os.environ["AWS_PROFILE"] if "AWS_PROFILE" in os.environ else None
    aws_profile = input(
        "Please enter the AWS_PROFILE name [Default: {}]: {}".format(
            env_aws_profile, env_aws_profile if env_aws_profile else ""
        )
    )
    if aws_profile == "":
        aws_profile = env_aws_profile

    env_aws_region = os.environ["AWS_REGION"] if "AWS_REGION" in os.environ else None
    aws_region = input(
        "Please enter the AWS_REGION name [Default: {}]: {}".format(
            env_aws_region, env_aws_region if env_aws_region else ""
        )
    )
    if aws_region == "":
        aws_region = env_aws_region

    boto_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    return boto_session


def login_ecr(boto_session):
    client = boto_session.client("ecr")
    response = client.get_authorization_token()
    username, password = base64.b64decode(response["authorizationData"][0]["authorizationToken"]).decode().split(":")
    endpoint = response["authorizationData"][0]["proxyEndpoint"]
    cli = docker.from_env()
    cli.login(username=username, password=password, registry=endpoint)

    return cli, endpoint


def build_docker_image(docker_cli, docker_registry):
    docker_tag = docker_registry.replace("https://", "") + "/" + DOCKER_IMAGE_TAG + ":latest"

    # TODO: Allow to use --cache-from to speed up this process bu using a prebuild remote image. It's important
    # that we don't entirely rely on the remote image since it's possible that the local code is different from the
    # public image (aka when we want to test local changes). --cache-from gives the best of both worlds.
    output = docker_cli.build(path=os.path.split(os.path.realpath(__file__))[0], tag=docker_tag, decode=True)
    logging.debug("Docker build output:")
    for line in output:
        logging.debug(line["stream"])

    return docker_tag


def execute_cloudformation_deployment(stack_name, boto_session, cloudformation_yaml_path):
    """
    Deploy the passed CloudFormation stack
    :param stack_name: Stack name
    :param boto_session: Boto3 session
    :param cloudformation_yaml_path: Cloudformation template yaml path
    """

    def convert_clouformation_output(output):
        """
        Convert CloudFormation output dict into a proper dict
        :param output: CloudFormation output dict
        :return: Proper dict
        """
        ret_dict = {}
        for entry in output:
            ret_dict[entry["OutputKey"]] = entry["OutputValue"]
        return ret_dict

    cloudformation_client = boto_session.client("cloudformation")
    with open(cloudformation_yaml_path, "r") as file:
        cloudformation_yaml = file.read()
        params = {"StackName": stack_name, "TemplateBody": cloudformation_yaml, "Capabilities": ["CAPABILITY_IAM"]}
        try:
            if _cloudformation_stack_exists(cloudformation_client=cloudformation_client, stack_name=stack_name):
                logging.info("Updating CloudFormation stack: %s", stack_name)
                cloudformation_client.update_stack(**params)
                waiter = cloudformation_client.get_waiter("stack_update_complete")
            else:
                logging.info("Creating CloudFormation stack: %s", stack_name)
                cloudformation_client.create_stack(**params)
                waiter = cloudformation_client.get_waiter("stack_create_complete")
            logging.info("...waiting for stack to be ready...")
            waiter.wait(StackName=stack_name)
            logging.info("CloudFormation stack changed successfully")
        except botocore.exceptions.ClientError as ex:
            error_message = ex.response["Error"]["Message"]
            if error_message == "No updates are to be performed.":
                logging.info("No CloudFormation changes")
            else:
                raise

    return convert_clouformation_output(
        cloudformation_client.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    )


def _cloudformation_stack_exists(cloudformation_client, stack_name):
    """
    Return whether a cloudformation stack already exists
    :param cloudformation_client: Boto3 CloudFormation client
    :param stack_name: Stack name
    :return: True or False
    """
    # Credit: https://gist.github.com/svrist/73e2d6175104f7ab4d201280acba049c
    stacks = cloudformation_client.list_stacks()["StackSummaries"]
    for stack in stacks:
        if stack["StackStatus"] == "DELETE_COMPLETE":
            continue
        if stack_name == stack["StackName"]:
            return True
    return False


def publish_docker_image(docker_cli, docker_tag):
    output = docker_cli.push(docker_tag, stream=True, decode=True)
    for line in output:
        logging.debug(line)


def run_ecs_task(boto_session, cloudformation_output):
    ecs_client = boto_session.client("ecs")

    ecs_client.run_task(
        cluster="baictl-ecs-cluster",
        taskDefinition=cloudformation_output["TaskDefinition"],
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [cloudformation_output["PublicSubnetOneArn"], cloudformation_output["PublicSubnetTwoArn"]],
                "securityGroups": [cloudformation_output["VpcDefaultSecurityGroupArn"]],
                "assignPublicIp": "ENABLED",
            }
        },
    )
    # TODO: Stream logs?


def destroy_cloudformation():
    # TODO: Ask whether CloudFormation stack should be destroyed again - this requires the ability to wait for the ECS task to finish first
    pass


if __name__ == "__main__":
    main()
