import logging
import json

import boto3
import urllib3

logging.basicConfig(level="INFO")


def build_federate_url(console_url):
    return (
        "https://isengard.amazon.com/federate?account=563267192464&role=Admin&destination="
        + console_url
        + "?region=us-east-1"
    )


def codepipeline(event):
    # Example event:
    # {
    #     "version": "0",
    #     "id": event_Id,
    #     "detail-type": "CodePipeline Pipeline Execution State Change",
    #     "source": "aws.codepipeline",
    #     "account": Pipeline_Account,
    #     "time": TimeStamp,
    #     "region": "us-east-1",
    #     "resources": [
    #         "arn:aws:codepipeline:us-east-1:account_ID:myPipeline"
    #     ],
    #     "detail": {
    #         "pipeline": "myPipeline",
    #         "version": "1",
    #         "state": "STARTED",
    #         "execution-id": execution_Id
    #     }
    # }
    execution_id = event["detail"]["execution-id"]
    pipeline = event["detail"]["pipeline"]

    console_url = f"codesuite/codepipeline/pipelines/{pipeline}/executions/{execution_id}/timeline"

    return f"Pipeline '{pipeline}' failed. See the execution here: {build_federate_url(console_url)}"


def codebuild(event):
    # Example event:
    # {
    #     "account": "123456789012",
    #     "detail": {
    #         "build-id": "arn:aws:codebuild:us-east-1:123456789012:build/SampleProjectName:a68ca311-846f-4ca4-b606-ae36de59542b",
    #         "build-status": "FAILED",
    #         "current-phase": "COMPLETED",
    #         "current-phase-context": "[]",
    #         "project-name": "SampleProjectName-master",
    #         "version": "1"
    #     },
    #     "detail-type": "CodeBuild Build State Change",
    #     "id": "1cb6e284-2c0a-4b4d-95f2-7dc042733d11",
    #     "region": "us-east-1",
    #     "resources": [
    #         "arn:aws:codebuild:us-east-1:123456789012:build/SampleProjectName:a68ca311-846f-4ca4-b606-ae36de59542b"
    #     ],
    #     "source": "aws.codebuild",
    #     "time": "2017-07-12T00:42:28Z",
    #     "version": "0"
    # }
    project = event["detail"]["project-name"]
    if not project.endswith("-master"):
        return None
    if event["detail"]["build-status"] != "FAILED":
        return None

    uid = event["detail"]["build-id"]
    uid = uid[uid.rindex(":") + 1 :]
    console_url = f"codesuite/codebuild/projects/{project}/build/{project}:{uid}/log"
    return f"Build of {project} failed. See log here: {build_federate_url(console_url)}"


def post_chime_message(message):
    post_fields = {"Content": message}

    session = boto3.session.Session()
    secrets_manager_client = session.client(service_name="secretsmanager", region_name="us-east-1")
    hook_url_secret = secrets_manager_client.get_secret_value(SecretId="ChimeHookUrl")
    hook_url = hook_url_secret["SecretString"]

    http = urllib3.PoolManager()
    response = http.request(
        "POST", hook_url, body=json.dumps(post_fields).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    print("Response data: %s" % response.data.decode("utf-8"))
    if response.status != 200:
        raise ValueError("Got a different than 200 response.status: %i" % response.status)


def lambda_handler(event, context):
    print(f"Got event: {event}")
    source = event["source"]
    handler = {"aws.codebuild": codebuild, "aws.codepipeline": codepipeline}[source]
    chime_message = handler(event)

    if chime_message:
        post_chime_message(chime_message)
    return {"statusCode": 200, "body": json.dumps("Hello from Lambda!")}
