import base64
import json
import logging
import datetime
import getpass
import hashlib
import socket
import uuid
import requests
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from dataclasses_json import dataclass_json
from pathlib import Path
from bai_kafka_utils.events import VisitedService, BenchmarkPayload, BenchmarkDoc, StatusMessageBenchmarkEvent
from .__version__ import __version__
from shutil import copy2
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

SERVICE_NAME = "bai-client-python"

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class SubmitEvent:
    message_id: str
    client_id: str
    client_version: str
    client_sha1: str
    client_username: str
    date: str
    visited: List[VisitedService]
    payload: BenchmarkPayload


def _sha1sum(string: str):
    sha1 = hashlib.sha1()
    sha1.update(string.encode("utf-8"))
    hexdigest = sha1.hexdigest()
    return hexdigest


def get_client_id() -> str:
    username = getpass.getuser()
    hostname = socket.gethostname()
    return _sha1sum(f"{username}+{hostname}")


def create_submit_event(descriptor_filename) -> SubmitEvent:
    now = datetime.datetime.utcnow()

    toml_file = Path(descriptor_filename)
    payload = BenchmarkPayload(
        toml=BenchmarkDoc(
            descriptor_filename=descriptor_filename,
            sha1=_sha1sum(toml_file.read_text()),
            doc=base64.b64encode(toml_file.read_bytes()).decode("utf-8"),
            contents={},
        )
    )
    return SubmitEvent(
        message_id=str(uuid.uuid4()),
        client_id=get_client_id(),
        client_version=__version__,
        client_sha1="??",  # declare -r MY_SHA1=$(sha1sum ${0} | awk '{print $1}')
        client_username=getpass.getuser(),
        date=now.strftime("%a %b %d %H:%M:%S %Z %Y"),
        visited=[VisitedService(svc=SERVICE_NAME, tstamp=int(now.timestamp()), version=__version__)],
        payload=payload,
    )


def _convert_status_json_response(json_string: str) -> List[StatusMessageBenchmarkEvent]:
    status_messages: List[Dict] = json.loads(json_string)

    # Deserializing and serializing each element looks like a very nasty hack, but I find it to be more elegant than
    # using `dacite` because dacite does not handle the convertion from `str` => `Enum`.
    ret = []
    for status_message_as_dict in status_messages:
        dumped_json = json.dumps(status_message_as_dict)
        try:
            status_message_event = StatusMessageBenchmarkEvent.from_json(dumped_json)
        except KeyError:
            if status_message_as_dict["visited"][-1]["svc"] == "bai-bff":
                # TODO: Fix StatusMessageBenchmarkEvent modeling status messages:
                #       https://github.com/MXNetEdge/benchmark-ai/issues/491
                continue
            logger.exception(f"Failed to deserialize the following json: {dumped_json}\n")
            raise
        ret.append(status_message_event)
    return ret


class BaiClient:
    """
    A "low-level" client for BAI.

    Each method is meant to be a 1:1 translation of the REST api provided by BAI.
    """

    SERVICE_ENDPOINT_PORT = "80"

    def __init__(self, endpoint=None):
        if endpoint is None:
            # Copy codebuild artifact to Anubis home dir
            artifact_output_file = Path(os.environ["CODEBUILD_SRC_DIR_service_endpoint_bff"] + "/bff/service_endpoint")
            anubis_home_dir = Path(os.environ["HOME"]).joinpath(".anubis")
            if not os.path.exists(anubis_home_dir):
                os.makedirs(anubis_home_dir)
            service_endpoint_file = copy2(artifact_output_file, Path(str(anubis_home_dir) + "/service_endpoint"))

            if service_endpoint_file.exists():
                endpoint = (
                    "http://"
                    + service_endpoint_file.read_text("utf-8").replace('"', "").replace("\n", "")
                    + f":{BaiClient.SERVICE_ENDPOINT_PORT}"
                )
            elif not artifact_output_file.exists():
                raise Exception(f"artifact_output_file not found at {artifact_output_file}")
            else:
                raise Exception(f"service_endpoint not found at {service_endpoint_file}")
        print(f"ENDPOINT: {endpoint}")
        self.endpoint = endpoint

    def submit(self, descriptor_filename: str) -> str:
        """
        :return: The action id
        """
        path = Path(descriptor_filename)
        if not path.exists():
            raise ValueError(f"Descriptor file does not exist: {path}")
        event = create_submit_event(descriptor_filename)
        event_to_json = event.to_json()
        with requests.Session() as session:
            logger.info(f"Submitting {path}")
            logger.debug(f"Submit event for {path}: {event} to {self.endpoint}")
            files = {"submit-event": (None, event_to_json)}
            response = session.post(self.endpoint + "/api/job/descriptor", files=files)
            self._handle_response(response)
            return response.text

    def status(self, action_id: str, client_id: str = None) -> Optional[List[StatusMessageBenchmarkEvent]]:
        if client_id is None:
            client_id = get_client_id()
        with requests.Session() as session:
            response = session.get(self.endpoint + f"/api/job/{client_id}/{action_id}?since=0")
            if response.status_code == 404:
                return None
            self._handle_response(response)
            return _convert_status_json_response(response.text)

    def ping(self):
        with requests.Session() as session:
            retries = Retry(total=30, backoff_factor=0.1)
            session.mount("http://", HTTPAdapter(max_retries=retries))
            print(f"session.get({self.endpoint}/ready)")
            response = session.get(self.endpoint + "/ready")
            self._handle_response(response)
            return response.status_code

    def _handle_response(self, response):
        if response.status_code != 200:
            raise ValueError(f"Bad response: {response.status_code} - {response.reason}")
