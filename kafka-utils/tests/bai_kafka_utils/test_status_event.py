import dataclasses

from bai_kafka_utils.events import (
    StatusMessageBenchmarkEvent,
    VisitedService,
    DataSet,
    FetcherPayload,
    FetcherBenchmarkEvent,
    Status,
)

FETCHER_PAYLOAD = FetcherPayload(datasets=[DataSet(src="SRC")], toml=None)

FETCHER_EVENT = FetcherBenchmarkEvent(
    action_id="OTHER_ACTION_ID",
    message_id="OTHER_MESSAGE_ID",
    client_id="OTHER_CLIENT_ID",
    client_version="0.1.0-481dad2",
    client_username="bellgav",
    authenticated=False,
    tstamp=1556814924121,
    visited=[VisitedService(svc="some", tstamp=1556814924121, version="1.0", node=None)],
    type="BAI_APP_FETCHER",
    payload=FETCHER_PAYLOAD,
)

STATUS_EVENT_JSON = (
    """
{
  "message_id": "MESSAGE_ID",
  "client_id":  "CLIENT_ID",
  "action_id":  "ACTION_ID",
  "tstamp": 1554901873677 ,
  "client_username": "vasya",
  "client_version": "1.0",
  "authenticated": true,
  "message": "Some fancy string as message",
  "status": "RUNNING",
  "visited": [{"node":"POD_NAME", "svc":"baictl", "tstamp":"1554901873677", "version":"v0.1.0-481dad1"}],
  "type": "BAI_APP_STATUS",
  "payload": %s
}
"""
    % FETCHER_PAYLOAD.to_json()
)

MESSAGE = "Some fancy string as message"

STATUS_EVENT = StatusMessageBenchmarkEvent(
    action_id="ACTION_ID",
    message_id="MESSAGE_ID",
    client_id="CLIENT_ID",
    client_version="1.0",
    client_username="vasya",
    authenticated=True,
    tstamp=1554901873677,
    visited=[VisitedService(svc="baictl", tstamp="1554901873677", version="v0.1.0-481dad1", node="POD_NAME")],
    type="BAI_APP_STATUS",
    status=Status.RUNNING,
    message=MESSAGE,
    payload=dataclasses.asdict(FETCHER_PAYLOAD),
)


def test_deserialization():
    deserialized = StatusMessageBenchmarkEvent.from_json(STATUS_EVENT_JSON)
    assert STATUS_EVENT == deserialized


def test_serialization():
    import json

    serialized = json.loads(STATUS_EVENT.to_json())
    expected = json.loads(STATUS_EVENT_JSON)

    assert serialized == expected


def test_create_from_event():
    event = StatusMessageBenchmarkEvent.create_from_event(Status.RUNNING, MESSAGE, FETCHER_EVENT)

    assert event.status == Status.RUNNING
    assert event.message == "Some fancy string as message"
    assert event.action_id == FETCHER_EVENT.action_id
    assert event.client_id == FETCHER_EVENT.client_id
    assert event.client_username == FETCHER_EVENT.client_username
    assert event.authenticated == FETCHER_EVENT.authenticated
    assert event.tstamp == FETCHER_EVENT.tstamp
    assert event.payload == dataclasses.asdict(FETCHER_PAYLOAD)
    assert event.visited == FETCHER_EVENT.visited