import json

import pytest

from bai_kafka_utils.events import (
    DataSet,
    FetcherPayload,
    ExecutorPayload,
    BenchmarkDoc,
    FetcherBenchmarkEvent,
    ExecutorBenchmarkEvent,
    create_from_object,
    BenchmarkEvent,
    FetcherStatus,
    FetchedType,
    CommandRequestPayload,
    BenchmarkJob,
)


@pytest.fixture
def base_event_as_dict():
    return {
        "action_id": "action-id",
        "message_id": "message-id",
        "client_id": "client-id",
        "client_version": "client_version",
        "client_username": "client_username",
        "authenticated": True,
        "tstamp": 150000,
        "visited": [],
        "type": "BAI_APP_BFF",
        "payload": {"toml": {"contents": {"name": "doc"}, "sha1": "sha1", "doc": "dst"}},
    }


@pytest.fixture
def base_event(base_event_as_dict):
    return BenchmarkEvent.from_json(json.dumps(base_event_as_dict))


@pytest.fixture
def dataset():
    return DataSet("http://foo.com")


# Rather a boundary test for DataSet optional
def test_data_set_optional_fields_just_src():
    json = '{"src":"http://foo.com"}'
    with pytest.warns(None) as record:
        dataset = DataSet.from_json(json)
        assert dataset == DataSet(src="http://foo.com")
    assert not record.list


def test_data_set_optional_missing_src():
    json = '{"dst":"http://foo.com", "md5":"42"}'
    with pytest.raises(KeyError):
        DataSet.from_json(json)


def test_data_set_dont_fail_unknown_fields():
    json = '{"src":"http://foo.com","foo":"bar"}'
    dataset = DataSet.from_json(json)
    assert not hasattr(dataset, "foo")


def test_data_set_with_enums():
    json = '{"src":"http://foo.com","type":"FILE", "status": "DONE"}'
    dataset = DataSet.from_json(json)
    assert dataset == DataSet(src="http://foo.com", type=FetchedType.FILE, status=FetcherStatus.DONE)


def test_data_set_with_enums_serialize():
    dataset = DataSet(src="http://foo.com", type=FetchedType.FILE, status=FetcherStatus.DONE)
    jsons = dataset.to_json()
    dict = json.loads(jsons)
    assert dict["type"] == "FILE"
    assert dict["status"] == "DONE"


# This was seen in the wild!
def test_crazy_json():
    json = (
        '{"toml":{"contents": {"name": "doc"},"sha1": "sha1","doc": "dst"}, '
        '"datasets" : [ [ {"src" : "s3://bucket/imagenet/train"}, { } ] ]}'
    )
    with pytest.raises(TypeError):
        FetcherPayload.from_json(json)


def test_fetcher_event(base_event_as_dict):
    fetcher_event_as_dict = base_event_as_dict
    fetcher_event_as_dict["payload"]["datasets"] = [{"src": "http://foo.com", "md5": "None", "dst": "None"}]
    event_as_json_string = json.dumps(fetcher_event_as_dict)

    event = FetcherBenchmarkEvent.from_json(event_as_json_string)
    assert type(event.payload) == FetcherPayload
    assert event.payload.toml is not None
    assert event.payload.datasets is not None


def test_executor_event(base_event_as_dict):
    executor_event_as_dict = base_event_as_dict
    executor_event_as_dict["payload"]["datasets"] = [{"src": "http://foo.com", "md5": "None", "dst": "None"}]
    executor_event_as_dict["payload"]["job"] = {"id": "job_id", "extras": {"some_var": "some_val"}}

    event_as_json_string = json.dumps(executor_event_as_dict)

    event = ExecutorBenchmarkEvent.from_json(event_as_json_string)
    assert type(event.payload) == ExecutorPayload
    assert event.payload.job == BenchmarkJob(id="job_id", extras={"some_var": "some_val"})


def test_benchmark_doc_all():
    json = (
        '{"contents":{"foo":"bar"},'
        ' "verified": false, "descriptor_filename":"foo.toml", "sha1":"SHA1", "doc":"BODY"}'
    )
    benchmark_doc = BenchmarkDoc.from_json(json)
    expected_doc = BenchmarkDoc(
        contents={"foo": "bar"}, verified=False, descriptor_filename="foo.toml", sha1="SHA1", doc="BODY"
    )
    assert benchmark_doc == expected_doc


def test_benchmark_doc_missing_sha1():
    json = '{"contents":{"foo":"bar"},' ' "verified": false, "descriptor_filename":"foo.toml", "doc":"BODY"}'
    with pytest.raises(KeyError):
        BenchmarkDoc.from_json(json)


def test_benchmark_doc_missing_optional():
    json = '{"contents":{"foo":"bar"},' ' "sha1":"SHA1", "doc":"BODY"}'
    benchmark_doc = BenchmarkDoc.from_json(json)
    assert benchmark_doc == BenchmarkDoc(contents={"foo": "bar"}, sha1="SHA1", doc="BODY")


def test_invalid_payload_type(base_event_as_dict):
    event_as_json_string = json.dumps(base_event_as_dict)
    event_type = FetcherBenchmarkEvent

    with pytest.raises(KeyError) as e:
        event_type.from_json(event_as_json_string)
    # Missing required dataset
    assert e.match("dataset")


def test_create_from_object(base_event_as_dict):
    event = BenchmarkEvent.from_json(json.dumps(base_event_as_dict))
    obj = create_from_object(FetcherBenchmarkEvent, event, payload=FetcherPayload(toml="", datasets=[]))
    assert type(obj) == FetcherBenchmarkEvent
    assert obj.action_id == event.action_id


def test_create_from_object_when_desired_class_is_not_a_dataclass(base_event):
    with pytest.raises(ValueError):
        create_from_object(object, base_event)


def test_create_from_object_when_input_object_is_not_a_dataclass():
    with pytest.raises(ValueError):
        create_from_object(FetcherBenchmarkEvent, object())


def test_create_from_object_when_specifying_field_with_wrong_type(base_event):
    with pytest.raises(ValueError):
        create_from_object(FetcherBenchmarkEvent, base_event, payload="payload")


def test_finals():
    assert not FetcherStatus.PENDING.final
    assert not FetcherStatus.RUNNING.final

    assert FetcherStatus.DONE.final
    assert FetcherStatus.FAILED.final


def test_fetch_type():
    assert str(FetchedType.FILE) == "FILE"


def test_fetch_status():
    assert str(FetcherStatus.DONE) == "DONE"


def test_cmd_payload_dict():
    json = '{"command":"doit", "args": {"foo":"bar"}}'
    payload = CommandRequestPayload.from_json(json)
    assert isinstance(payload.args, dict)
    assert payload.args == {"foo": "bar"}


def test_cmd_payload_list():
    json = '{"command":"doit", "args": ["foo", "bar"]}'
    payload = CommandRequestPayload.from_json(json)
    assert isinstance(payload.args, list)
    assert payload.args == ["foo", "bar"]
