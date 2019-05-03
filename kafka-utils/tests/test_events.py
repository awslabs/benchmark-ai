import json

import pytest

from bai_kafka_utils.events import DataSet, FetcherPayload, ExecutorPayload, BenchmarkDoc, \
    VisitedService, FetcherBenchmarkEvent, ExecutorBenchmarkEvent


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
        "payload": {
            "toml": {
                "contents": {"name": "doc"},
                "sha1": "sha1",
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


# This was seen in the wild!
def test_crazy_json():
    json = '{"toml":{"contents": {"name": "doc"},"sha1": "sha1","doc": "dst"}, ' \
           '"datasets" : [ [ {"src" : "s3://bucket/imagenet/train"}, { } ] ]}'
    with pytest.raises(TypeError):
        FetcherPayload.from_json(json)


def test_fetcher_event(base_event_as_dict):
    fetcher_event_as_dict = base_event_as_dict
    fetcher_event_as_dict["payload"]["datasets"] = [
        {"src": "http://foo.com", "md5": "None", "dst": "None"}
    ]
    event_as_json_string = json.dumps(fetcher_event_as_dict)

    event = FetcherBenchmarkEvent.from_json(event_as_json_string)
    assert type(event.payload) == FetcherPayload
    assert event.payload.toml is not None
    assert event.payload.datasets is not None


def test_executor_event(base_event_as_dict):
    executor_event_as_dict = base_event_as_dict
    executor_event_as_dict["payload"]["datasets"] = [{"src": "http://foo.com", "md5": "None", "dst": "None"}]
    executor_event_as_dict["payload"]["job"] = {"id": "job_id", "status": "status", "k8s_yaml": "yaml_file"}

    event_as_json_string = json.dumps(executor_event_as_dict)

    event = ExecutorBenchmarkEvent.from_json(event_as_json_string)
    assert type(event.payload) == ExecutorPayload
    assert event.payload.job.id == "job_id"
    assert event.payload.job.status == "status"
    assert event.payload.job.k8s_yaml == "yaml_file"
    assert event.payload.job.output is None


def test_benchmark_doc_all():
    json = '{"contents":{"foo":"bar"},' \
           ' "verified": false, "descriptor_filename":"foo.toml", "sha1":"SHA1", "doc":"BODY"}'
    benchmark_doc = BenchmarkDoc.from_json(json)
    expected_doc = \
        BenchmarkDoc(contents={"foo": "bar"}, verified=False, descriptor_filename="foo.toml", sha1="SHA1", doc="BODY")
    assert benchmark_doc == expected_doc


def test_benchmark_doc_missing_sha1():
    json = '{"contents":{"foo":"bar"},' \
           ' "verified": false, "descriptor_filename":"foo.toml", "doc":"BODY"}'
    with pytest.raises(KeyError):
        BenchmarkDoc.from_json(json)


def test_benchmark_doc_missing_optional():
    json = '{"contents":{"foo":"bar"},' \
           ' "sha1":"SHA1", "doc":"BODY"}'
    benchmark_doc = BenchmarkDoc.from_json(json)
    assert benchmark_doc == BenchmarkDoc(contents={"foo": "bar"}, sha1="SHA1", doc="BODY")


def test_invalid_payload_type(base_event_as_dict):
    event_as_json_string = json.dumps(base_event_as_dict)
    event_type = FetcherBenchmarkEvent

    with pytest.raises(KeyError) as e:
        event_type.from_json(event_as_json_string)
    # Missing required dataset
    assert e.match("dataset")


BIG_JSON = '''{
               "date": "Thu May 02 16:15:42 UTC 2019",
               "authenticated": false,
               "payload": {
                   "toml": {
                       "descriptor_filename": "example_descriptor2.toml",
                       "sha1": "be60cb85620fa041c1bfabd9a9b1c8c1d6be1c78",
                       "doc": "IyBCZW5jaG1hcYS90Zi1pbWFnZW5ldC8iCg==",
                       "verified": true,
                       "contents": {
                           "spec_version": "0.1.0",
                           "data": {
                               "sources": [
                                   {
                                       "path": "~/data/tf-imagenet/",
                                       "uri": "s3://bucket/imagenet/train"
                                   },
                                   {
                                       "path": "~/data/tf-imagenet/",
                                       "uri": "s3://bucket/imagenet/validation"
                                   }
                               ],
                               "id": "imagenet"
                           },
                           "env": {
                               "privileged": false,
                               "extended_shm": true,
                               "docker_image": "user/repo:tag"
                           },
                           "info": {
                               "task_name": "Example benchmark",
                               "scheduling": "single_run",
                               "description": " Full job description."
                           },
                           "hardware": {
                               "distributed": {
                                   "num_instances": 3
                               },
                               "strategy": "horovod",
                               "instance_type": "p3.8xlarge"
                           },
                           "ml": {
                               "args": "--model=resnet50_v2 --batch-size=32",
                               "benchmark_code": "python /root/train.sh"
                           }
                       }
                   },
                   "datasets": [
                       {
                           "path": "~/data/tf-imagenet/",
                           "src": "s3://bucket/imagenet/train"
                       },
                       {
                           "src": "s3://bucket/imagenet/validation"
                       }
                   ]
               },
               "tstamp": 1556814924121,
               "client_username": "bellgav",
               "action_id": "ffea52eb-c24b-4dd0-b32e-61230db34ad5",
               "visited": [
                   {
                       "svc": "baictl-client",
                       "tstamp": "@@TSTAMP@@",
                       "version": "0.1.0-481dad2"
                   },
                   {
                       "svc": "bai-bff",
                       "tstamp": 1556814924121,
                       "version": "0.0.2"
                   }
               ],
               "message_id": "007bd9f8-f564-4edb-bb48-7380ee562ffc",
               "client_sha1": "c05467317b6765535f1ec60f0aee812d39b35dd2",
               "client_id": "97e7eb322342626974fb171fc5793514b0aea789",
               "client_version": "0.1.0-481dad2"
           }'''

EXPECTED_CONTENTS = {"spec_version": "0.1.0", "data": {
    "sources": [{"path": "~/data/tf-imagenet/", "uri": "s3://bucket/imagenet/train"},
                {"path": "~/data/tf-imagenet/", "uri": "s3://bucket/imagenet/validation"}], "id": "imagenet"},
                     "env": {"privileged": False,
                             "extended_shm": True,
                             "docker_image": "user/repo:tag"},
                     "info": {
                         "task_name": "Example benchmark",
                         "scheduling": "single_run",
                         "description": " Full job description."},
                     "hardware": {
                         "distributed": {
                             "num_instances": 3},
                         "strategy": "horovod",
                         "instance_type": "p3.8xlarge"},
                     "ml": {
                         "args": "--model=resnet50_v2 --batch-size=32",
                         "benchmark_code": "python /root/train.sh"}}

EXPECTED_DOC = BenchmarkDoc(doc="IyBCZW5jaG1hcYS90Zi1pbWFnZW5ldC8iCg==",
                            sha1="be60cb85620fa041c1bfabd9a9b1c8c1d6be1c78", contents=EXPECTED_CONTENTS, verified=True,
                            descriptor_filename="example_descriptor2.toml")

EXPECTED_VISITED = [
    VisitedService(
        svc="baictl-client",
        tstamp="@@TSTAMP@@",
        version="0.1.0-481dad2"
    ),
    VisitedService(
        svc="bai-bff",
        tstamp=1556814924121,
        version="0.0.2"
    )
]

EXPECTED_DATASETS = [
    DataSet("s3://bucket/imagenet/train"),
    DataSet("s3://bucket/imagenet/validation")
]

EXPECTED_EVENT = FetcherBenchmarkEvent(
    action_id="ffea52eb-c24b-4dd0-b32e-61230db34ad5",
    message_id="007bd9f8-f564-4edb-bb48-7380ee562ffc",
    client_id="97e7eb322342626974fb171fc5793514b0aea789",
    client_version="0.1.0-481dad2",
    client_username="bellgav",
    authenticated=False,
    tstamp=1556814924121,
    visited=EXPECTED_VISITED,
    payload=FetcherPayload(datasets=EXPECTED_DATASETS,
                           toml=EXPECTED_DOC)
)


def test_big_json():
    event = FetcherBenchmarkEvent.from_json(BIG_JSON)
    assert event == EXPECTED_EVENT
