import textwrap
import pytest

from bai_kafka_utils.events import DataSet, BenchmarkEvent, BenchmarkPayload, BenchmarkDoc


@pytest.fixture
def benchmark_doc():
    return BenchmarkDoc({'name': 'doc'}, 'md5', 'dst')


@pytest.fixture
def benchmark_payload(benchmark_doc):
    return BenchmarkPayload(benchmark_doc)


@pytest.fixture
def benchmark_event(benchmark_payload):
    return BenchmarkEvent(
        'request-id',
        'message-id',
        'client-id',
        'client_version',
        'client_user',
        True,
        150000,
        [],
        benchmark_payload
    )


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


def test_fetcher_event():
    json = textwrap.dedent(
        """{"request_id":"request-id",
            "message_id":"message-id",
            "client_id":"client-id",
            "client_version":"client_version",
            "client_user":"client_user",
            "authenticated":"True",
            "date":150000,
            "visited":[],
            "payload":{
              "toml":{"contents":{"name": "doc"}, "md5":"md5", "doc":"dst"},
              "data_sets":[{"src":"http://foo.com", "md5":"None", "dst":"None"}]
              }}""".replace('\n', ''))

    event = BenchmarkEvent.from_json(json)
    assert type(event.payload) == BenchmarkPayload
    assert event.payload.toml is not None
    assert event.payload.data_sets is not None


def test_executor_event():
    json = textwrap.dedent(
        """{"request_id":"request-id",
            "message_id":"message-id",
            "client_id":"client-id",
            "client_version":"client_version",
            "client_user":"client_user",
            "authenticated":"True",
            "date":150000,
            "visited":[],
            "payload":{
              "toml":{"contents":{"name": "doc"}, "md5":"md5", "doc":"dst"},
              "data_sets":[{"src":"http://foo.com", "md5":"None", "dst":"None"}],
              "job":{"id":"job_id", "status":"status", "k8s_yaml":"yaml_file"}
              }}""".replace('\n', ''))

    event = BenchmarkEvent.from_json(json)
    assert event.payload.job.id == "job_id"
    assert event.payload.job.status == "status"
    assert event.payload.job.k8s_yaml == "yaml_file"
    assert event.payload.job.out is None
