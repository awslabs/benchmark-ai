import json

import pytest

import bai_kafka_utils.events
from bai_kafka_utils.events import DataSet, FetcherPayload, ExecutorPayload


@pytest.fixture
def base_event_as_dict():
    return {
        "action_id": "action-id",
        "message_id": "message-id",
        "client_id": "client-id",
        "client_version": "client_version",
        "client_user": "client_user",
        "authenticated": True,
        "date": 150000,
        "visited": [],
        "payload": {
            "toml": {
                "contents": {"name": "doc"},
                "md5": "md5",
                "doc": "dst"
            }
        }
    }


@pytest.fixture
def dataset():
    return DataSet("http://foo.com")


# Rather a boundary test for DataSet optional
def test_data_set_optional_fields_just_src():
    json = '{"src":"http://foo.com"}'
    with pytest.warns(None) as record:
        DataSet.from_json(json)
    assert not record.list


def test_data_set_optional_missing_src():
    json = '{"dst":"http://foo.com", "md5":"42"}'
    with pytest.raises(KeyError):
        DataSet.from_json(json)


def test_data_set_dont_fail_unknown_fields():
    json = '{"src":"http://foo.com","foo":"bar"}'
    dataset = DataSet.from_json(json)
    assert not hasattr(dataset, "foo")


def test_fetcher_event(base_event_as_dict):
    fetcher_event_as_dict = base_event_as_dict
    fetcher_event_as_dict["payload"]["data_sets"] = [
        {"src": "http://foo.com", "md5": "None", "dst": "None"}
    ]
    event_as_json_string = json.dumps(fetcher_event_as_dict)

    event_type = bai_kafka_utils.events.make_benchmark_event(FetcherPayload)
    event = event_type.from_json(event_as_json_string)
    assert type(event.payload) == FetcherPayload
    assert event.payload.toml is not None
    assert event.payload.data_sets is not None


def test_executor_event(base_event_as_dict):
    executor_event_as_dict = base_event_as_dict
    executor_event_as_dict["payload"]["data_sets"] = [{"src": "http://foo.com", "md5": "None", "dst": "None"}]
    executor_event_as_dict["payload"]["job"] = {"id": "job_id", "status": "status", "k8s_yaml": "yaml_file"}

    event_as_json_string = json.dumps(executor_event_as_dict)

    event_type = bai_kafka_utils.events.make_benchmark_event(ExecutorPayload)
    event = event_type.from_json(event_as_json_string)
    assert type(event.payload) == ExecutorPayload
    assert event.payload.job.id == "job_id"
    assert event.payload.job.status == "status"
    assert event.payload.job.k8s_yaml == "yaml_file"
    assert event.payload.job.output is None


def test_invalid_payload_type(base_event_as_dict):
    event_as_json_string = json.dumps(base_event_as_dict)
    event_type = bai_kafka_utils.events.make_benchmark_event(FetcherPayload)

    with pytest.raises(KeyError) as e:
        event_type.from_json(event_as_json_string)
    assert e.match("data_set")
