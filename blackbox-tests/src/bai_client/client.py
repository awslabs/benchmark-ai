import base64

import datetime
import getpass
import hashlib
import socket
from dataclasses import dataclass
from typing import Any, List

from dataclasses_json import dataclass_json
from pathlib import Path
import uuid
import requests

from bai_kafka_utils.events import VisitedService, BenchmarkPayload, BenchmarkDoc
from .__version__ import __version__

SERVICE_NAME = "bai-client"


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
    return sha1.hexdigest()


def get_client_id() -> str:
    username = getpass.getuser()
    hostname = socket.gethostname()
    return _sha1sum(f"{username}+{hostname}")


def create_submit_event(descriptor_filename) -> SubmitEvent:
    now = datetime.datetime.utcnow()

    toml_contents_as_bytes = Path(descriptor_filename).read_bytes()
    payload = BenchmarkPayload(
        toml=BenchmarkDoc(
            descriptor_filename=descriptor_filename,
            sha1=_sha1sum(descriptor_filename),
            doc=base64.b64encode(toml_contents_as_bytes).decode("utf-8"),
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


class BaiClient:
    """
    A "low-level" client for BAI.

    Each method is meant to be a 1:1 translation of the REST api provided by BAI.
    """

    BAI_HOME = Path.home() / ".bai"

    def __init__(self, endpoint=None):
        if endpoint is None:
            service_endpoint_file = BaiClient.BAI_HOME / "service_endpoint"
            if service_endpoint_file.exists():
                endpoint = "http://" + service_endpoint_file.read_text("utf-8").strip()
            else:
                endpoint = "http://localhost:8080"
        self.endpoint = endpoint

    def submit(self, descriptor_filename) -> str:
        """
        :return: The action id
        """
        path = Path(descriptor_filename)
        if not path.exists():
            raise ValueError(f"Descriptor file does not exist: {path}")
        event = create_submit_event(descriptor_filename)
        event_to_json = event.to_json()
        with requests.Session() as session:
            response = session.post(self.endpoint + "/api/job/descriptor", data=event_to_json)
            if response.status_code != 200:
                raise ValueError(f"Bad response: {response.status_code} - {response.reason}")
            return response.text
