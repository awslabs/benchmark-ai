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
import config
import argparse
import time


CFN_SPLIT_STRING = "|||"
DOCKER_IMAGE_TAG = "benchmark-ai/baictl"
CLOUDFORMATION_YAML_PATH = os.path.join(os.path.split(os.path.realpath(__file__))[0], "cfn-baictl-ecs.yml")
CONFIG_YAML_PATH = os.path.join(os.path.split(os.path.realpath(__file__))[0], "config.yml")
ECS_CLUSTER_NAME = "baictl-ecs-cluster"
LOG_STREAM_WAIT_SECONDS = 300


def main():
    parser = argparse.ArgumentParser(description="Run baictl create/destroy infra remotely")
    parser.add_argument("mode", help="create or destroy", nargs="?", choices=("create", "destroy"))
    parser.add_argument("--debug", help="verbose debug output", action="store_true", default=False)
    args = parser.parse_args()
    if not args.mode:
        raise ValueError('Please pass either "create" or "destroy".')

    logger = logging.getLogger()
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter("%(asctime)s- %(levelname)s - %(message)s"))
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG) if args.debug else logging.getLogger().setLevel(logging.INFO)

    config = load_config(CONFIG_YAML_PATH)

    boto_session = request_aws_credentials(aws_region=config.get_aws_region())
    docker_cli, docker_registry = login_ecr(boto_session=boto_session)
    docker_tag = build_docker_image(docker_cli=docker_cli, docker_registry=docker_registry)
    cloudformation_output = execute_cloudformation_deployment(
        stack_name="baictl-ecs",
        boto_session=boto_session,
        cloudformation_yaml_path=CLOUDFORMATION_YAML_PATH,
        baictl_command=generate_baictl_command(config=config, mode=args.mode),
    )
    cloudwatch_log_group = cloudformation_output["BaictlLogGroupName"]
    docker_cli, docker_registry = login_ecr(boto_session=boto_session)
    publish_docker_image(docker_cli=docker_cli, docker_tag=docker_tag, docker_registry=docker_registry)
    ecs_task_response = run_ecs_task(
        boto_session=boto_session, cloudformation_output=cloudformation_output, ecs_cluster_name=ECS_CLUSTER_NAME
    )
    cloudwatch_log_stream, task_arn = parse_ecs_response(ecs_task_response)
    get_cloudwatch_logs(
        boto_session=boto_session,
        cloudwatch_log_group=cloudwatch_log_group,
        cloudwatch_log_stream=cloudwatch_log_stream,
        aws_region=config.get_aws_region(),
    )
    check_ecs_task(boto_session=boto_session, ecs_cluster_name=ECS_CLUSTER_NAME, task_arn=task_arn)
    destroy_cloudformation()


def load_config(path):
    return config.Config(path)


def generate_baictl_command(config, mode):
    return [
        mode,  # create or destroy
        "infra",
        "--aws-prefix-list-id=" + config.get_aws_prefix_lists(),
        "--aws-region=" + config.get_aws_region(),
    ]


def request_aws_credentials(aws_region):
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

    boto_session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    return boto_session


def login_ecr(boto_session):
    client = boto_session.client("ecr")
    response = client.get_authorization_token()
    username, password = base64.b64decode(response["authorizationData"][0]["authorizationToken"]).decode().split(":")
    endpoint = response["authorizationData"][0]["proxyEndpoint"]
    cli = docker.from_env()
    result = cli.login(username=username, password=password, registry=endpoint)
    if result["Status"] != "Login Succeeded":
        logging.error("Error logging in to Docker registry")
        logging.error(result)
        raise Exception(result)

    return cli, endpoint


def build_docker_image(docker_cli, docker_registry):
    logging.info("Building Docker image")
    docker_tag = docker_registry.replace("https://", "") + "/" + DOCKER_IMAGE_TAG + ":latest"

    # TODO: Allow to use --cache-from to speed up this process bu using a prebuild remote image. It's important
    # that we don't entirely rely on the remote image since it's possible that the local code is different from the
    # public image (aka when we want to test local changes). --cache-from gives the best of both worlds.
    output = docker_cli.build(
        path=os.path.dirname(os.path.split(os.path.realpath(__file__))[0]),  # Context is ../cwd
        tag=docker_tag,
        dockerfile=os.path.join(os.path.split(os.path.realpath(__file__))[0], "Dockerfile-baictl"),
        decode=True,
    )
    logging.debug("Docker build output:")
    for line in output:
        try:
            message = line["stream"] if "stream" in line else line["status"]
            logging.debug(message)
        except KeyError as e:
            logging.error(line)
            logging.exception(e)
            raise e
    return docker_tag


def execute_cloudformation_deployment(stack_name, boto_session, cloudformation_yaml_path, baictl_command):
    """
    Deploy the passed CloudFormation stack
    :param stack_name: Stack name
    :param boto_session: Boto3 session
    :param cloudformation_yaml_path: Cloudformation template yaml path
    :param baictl_command: List of commands to run. e.g. ['create', 'infra']
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
        params = {
            "StackName": stack_name,
            "TemplateBody": cloudformation_yaml,
            "Capabilities": ["CAPABILITY_IAM"],
            "Parameters": [
                {
                    "ParameterKey": "CommandToExecute",
                    "ParameterValue": CFN_SPLIT_STRING.join(
                        baictl_command
                    ),  # CloudFormation doesn't support List of Strings..
                    "UsePreviousValue": False,
                }
            ],
        }
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


def publish_docker_image(docker_cli, docker_tag, docker_registry):
    logging.info("Publishing docker image, this might take ~15 minutes")

    output = docker_cli.push(
        docker_tag,
        stream=True,
        decode=True,
        # The docker cli is not smart enough to distinguish between https:// as prefix for the registry and without
        # https, so we have to do it manually...
        auth_config=docker_cli._auth_configs[docker_registry],
    )
    for line in output:
        logging.debug(line)
        if "errorDetail" in line:
            logging.error("Error during docker push:" + line["errorDetail"]["message"])
            raise Exception(line["errorDetail"]["message"])


def run_ecs_task(boto_session, cloudformation_output, ecs_cluster_name):
    logging.info("Executing infrastructure build on AWS Elastic Container Service")
    ecs_client = boto_session.client("ecs")

    # Check that the task is not currently running
    if len(ecs_client.list_tasks(cluster=ecs_cluster_name)["taskArns"]) != 0:
        logging.error("ECS cluster {} has ongoing tasks".format(ecs_cluster_name))
        raise Exception("Aborting!  There is a task already creating Anubis infrastructure!")

    logging.info("Running ECS Task to create infrastructure")
    resp = ecs_client.run_task(
        cluster=ecs_cluster_name,
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

    return resp


class ECS_Status:
    running = ["RUNNING", "PENDING"]
    complete = ["STOPPED", "DEPROVISIONING"]


def check_ecs_task(boto_session, ecs_cluster_name, task_arn):
    ecs_client = boto_session.client("ecs")
    first_log_line = True
    ecs_wait_time = 5

    while True:
        response = ecs_client.describe_tasks(cluster=ecs_cluster_name, tasks=[task_arn])
        ecs_task = response["tasks"][0]
        task_status = ecs_task["lastStatus"]
        failures = response["failures"]

        if task_status in ECS_Status.running:
            if first_log_line:
                logging.info("Waiting for ECS task to finish...")
                first_log_line = False
            else:
                logging.debug("Still waiting for ECS task to finish")
            time.sleep(ecs_wait_time)
        elif task_status in ECS_Status.complete:
            container_status = ecs_task["containers"][0]["exitCode"]

            if container_status != 0:
                logging.error(
                    "Anubis infrastructure creation failed with exit code {}.  Check cloudwatch log link above for details.".format(
                        container_status
                    )
                )
                break
            elif len(failures) != 0:
                for failure in failures:
                    logging.error("Failure on RESOURCE: {} REASON: {}".format(failure["arn"], failure["reason"]))
                raise Exception("Failure(s) in ECS task to build infrastructure")
            else:
                logging.info("Complete!  Anubis infrastructure is ready")
                logging.debug("ECS Task Response: {}".format(response))
                break
        else:
            logging.error("Unable to get task return status \nResponse: {}".format(response))
            raise Exception("Failure to return ECS Task status")


def destroy_cloudformation():
    # TODO: Ask whether CloudFormation stack should be destroyed again - this requires the ability to wait for the ECS task to finish first
    pass


def get_cloudwatch_logs(boto_session, cloudwatch_log_group, cloudwatch_log_stream, aws_region):
    logs_client = boto_session.client("logs")
    LOG_STREAM_INCREMENT_SECONDS = 10
    logging.info("Waiting for logs, this should take less than 60 seconds")

    # Wait 5 minutes for cloudwatch log stream to show up
    for wait_seconds in range(0, LOG_STREAM_WAIT_SECONDS, LOG_STREAM_INCREMENT_SECONDS):
        log_streams = logs_client.describe_log_streams(
            logGroupName=cloudwatch_log_group, orderBy="LastEventTime", descending=True
        )["logStreams"]

        log_streams_names = []
        for stream in log_streams:
            log_streams_names.append(stream["logStreamName"])

        if cloudwatch_log_stream in log_streams_names:
            logging.info(
                "Cloudwatch log for run here: https://console.aws.amazon.com/cloudwatch/home?region={}#logEventViewer:group={};stream={}".format(
                    aws_region, cloudwatch_log_group, cloudwatch_log_stream
                )
            )
            break
        logging.debug("Waited {} seconds for Cloudwatch log stream...".format(wait_seconds))
        time.sleep(LOG_STREAM_INCREMENT_SECONDS)
    else:
        logging.error("Can not find Cloudwatch log Stream {} -> {}".format(cloudwatch_log_group, cloudwatch_log_stream))

    # TODO: Stream Logs?


def parse_ecs_response(ecs_task_response):
    ecs_task = ecs_task_response["tasks"][0]
    ecs_prefix_name = ecs_task["overrides"]["containerOverrides"][0]["name"]
    ecs_container_name = ecs_task["containers"][0]["name"]
    ecs_task_id = ecs_task["taskArn"].split("/")[-1]
    cloudwatch_log_stream = ecs_prefix_name + "/" + ecs_container_name + "/" + ecs_task_id
    task_arn = ecs_task["taskArn"]
    return cloudwatch_log_stream, task_arn


if __name__ == "__main__":
    main()
