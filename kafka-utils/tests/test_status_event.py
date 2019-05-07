from bai_kafka_utils.events import (
    StatusMessageBenchmarkEvent,
    VisitedService,
    StatusMessagePayload,
    DataSet,
    FetcherPayload,
    FetcherBenchmarkEvent,
)
from bai_kafka_utils.status_message import create_status_message_event

FETCHER_EVENT = EXPECTED_FETCHER_EVENT = FetcherBenchmarkEvent(
    action_id="OTHER_ACTION_ID",
    message_id="OTHER_MESSAGE_ID",
    client_id="OTHER_CLIENT_ID",
    client_version="0.1.0-481dad2",
    client_username="bellgav",
    authenticated=False,
    tstamp=1556814924121,
    visited=[VisitedService(svc="some", tstamp=1556814924121, version="1.0")],
    payload=FetcherPayload(datasets=[DataSet(src="SRC")], toml=None),
)

STATUS_EVENT_JSON = """
{
  "message_id": "MESSAGE_ID",
  "client_id":  "CLIENT_ID",
  "action_id":  "ACTION_ID",
  "tstamp": 1554901873677 ,
  "client_username": "vasya",
  "client_version": "1.0",
  "authenticated": true,
  "visited": [{"svc":"baictl", "tstamp":"1554901873677", "version":"v0.1.0-481dad1"}],
    "payload":{
      "message": "SOME STRING"
    }
}
"""

MESSAGE = "SOME STRING"

EXPECTED_STATUS_MESSAGE_PAYLOAD = StatusMessagePayload(MESSAGE)


EXPECTED_STATUS_EVENT = StatusMessageBenchmarkEvent(
    action_id="ACTION_ID",
    message_id="MESSAGE_ID",
    client_id="CLIENT_ID",
    client_version="1.0",
    client_username="vasya",
    authenticated=True,
    tstamp=1554901873677,
    visited=[VisitedService(svc="baictl", tstamp="1554901873677", version="v0.1.0-481dad1")],
    payload=EXPECTED_STATUS_MESSAGE_PAYLOAD,
)


def test_status_event():
    assert EXPECTED_STATUS_EVENT == StatusMessageBenchmarkEvent.from_json(STATUS_EVENT_JSON)


def test_create_one_from_other():
    event = create_status_message_event(FETCHER_EVENT, MESSAGE)

    assert event.action_id == FETCHER_EVENT.action_id
    assert event.client_id == FETCHER_EVENT.client_id
    assert event.client_username == FETCHER_EVENT.client_username
    assert event.authenticated == FETCHER_EVENT.authenticated
    assert event.tstamp == FETCHER_EVENT.tstamp
    assert event.payload == EXPECTED_STATUS_MESSAGE_PAYLOAD
    assert event.visited == []
