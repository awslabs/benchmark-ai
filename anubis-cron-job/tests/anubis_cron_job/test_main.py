import os
from unittest.mock import MagicMock

import kafka
import pytest
from pytest_cases import pytest_parametrize_plus, fixture_ref

from anubis_cron_job import __main__

BENCHMARK_EVENT = (
    '{"action_id": "2b31d067-8d37-4287-9944-aa794468bc9f", "message_id":'
    '"5b137a70-cbf1-4d52-9c5c-e208e4f3cbb1", "client_id": "19c104987141a846c0bbd688678c23fed19a5742",'
    '"client_version": "0.1.0-481dad2", "client_username": "bob",'
    '"authenticated": false, "tstamp": 1565094802391, "visited": [{"svc":'
    '"anubis-client", "tstamp": 1565094802000, "version": "0.1.0-481dad2",'
    '"node": null}, {"svc": "bai-bff", "tstamp": 1565094802391, "version":'
    '"0.2.0", "node": "bai-bff-76b85ffb76-cdsrp"}, {"svc": "fetcher-dispatcher",'
    '"tstamp": 1565094802505, "version": "1.0", "node": "fetcher-dispatcher-76dddd5797-wj5kg"}],'
    '"type": "BAI_APP_FETCHER", "payload": {"toml": {"contents": {"output":'
    '{"metrics": ["epoch", "train_loss", "loss", "accuracy"]}, "spec_version":'
    '"0.1.0", "env": {"docker_image": "benchmarkai/hello-world:latest"},'
    '"info": {"task_name": "Hello world", "scheduling": "*/1 * * * *",'
    '"description": " A hello world example of using Benchmark AI"}, "hardware":'
    '{"strategy": "single_node", "instance_type": "t3.small"}, "ml": {"benchmark_code":'
    '"python3 hello-world.py"}}, "doc": "IyBCZW5jaG1hcmtBSSBtZXRhCnNwZWNfdmVyc2lvbiA9ICIwLjEuMCIKCiMgVGhlc2UgZmll'
    "bGRzIGRvbid0IGhhdmUgYW55IGltcGFjdCBvbiB0aGUgam9iIHRvIHJ1biwgdGhleSBjb250YWluCiMgbWVyZWx5IGluZm9ybWF0aXZlIGRh"
    "dGEgc28gdGhlIGJlbmNobWFyayBjYW4gYmUgY2F0ZWdvcml6ZWQgd2hlbiBkaXNwbGF5ZWQKIyBpbiB0aGUgZGFzaGJvYXJkLgpbaW5mb10K"
    "dGFza19uYW1lID0gIkhlbGxvIHdvcmxkIgpkZXNjcmlwdGlvbiA9ICIiIiBcCiAgICBBIGhlbGxvIHdvcmxkIGV4YW1wbGUgb2YgdXNpbmcgQ"
    "mVuY2htYXJrIEFJXAogICAgIiIiCnNjaGVkdWxpbmcgPSAiKi8xICogKiAqICoiCgojIDEuIEhhcmR3YXJlCltoYXJkd2FyZV0KaW5zdGFuY2"
    "VfdHlwZSA9ICJ0My5zbWFsbCIKc3RyYXRlZ3kgPSAic2luZ2xlX25vZGUiCgojIDIuIEVudmlyb25tZW50CltlbnZdCiMgRG9ja2VyIGh1YiA"
    "8aHViLXVzZXI+LzxyZXBvLW5hbWU+Ojx0YWc+IApkb2NrZXJfaW1hZ2UgPSAiYmVuY2htYXJrYWkvaGVsbG8td29ybGQ6bGF0ZXN0IgoKIyAz"
    "LiBNYWNoaW5lIGxlYXJuaW5nIHJlbGF0ZWQgc2V0dGluZ3M6IAojIGRhdGFzZXQsIGJlbmNobWFyayBjb2RlIGFuZCBwYXJhbWV0ZXJzIGl0I"
    "HRha2VzClttbF0KYmVuY2htYXJrX2NvZGUgPSAicHl0aG9uMyBoZWxsby13b3JsZC5weSIKCiMgNC4gT3V0cHV0CltvdXRwdXRdCiMgRGVmaW"
    "5lIHdoaWNoIG1ldHJpY3Mgd2lsbCBiZSB0cmFja2VkIGluIHRoaXMgYmVuY2htYXJrCm1ldHJpY3MgPSBbImVwb2NoIiwgInRyYWluX2xvc3M"
    'iLCAibG9zcyIsICJhY2N1cmFjeSJdCg==",'
    '"sha1": "6e38ce3d47171fbb387237e1c61e3feaba6c3b78", "descriptor_filename":'
    '"descriptor.toml", "verified": true}, "datasets": [], "scripts": []}}'
)

KAFKA_BOOTSTRAP_SERVERS = ["a", "b", "c"]
PRODUCER_TOPIC = "topic"


@pytest.fixture
def mock_bootstrap_servers():
    return ",".join(KAFKA_BOOTSTRAP_SERVERS)


@pytest.fixture
def mock_benchmark_event():
    return BENCHMARK_EVENT


@pytest.fixture
def mock_producer_topic():
    return PRODUCER_TOPIC


@pytest.fixture
def mock_env(mocker, mock_bootstrap_servers, mock_producer_topic, mock_benchmark_event):

    env = {
        "KAFKA_BOOTSTRAP_SERVERS": mock_bootstrap_servers,
        "PRODUCER_TOPIC": mock_producer_topic,
        "BENCHMARK_EVENT": mock_benchmark_event,
    }

    mocker.patch.object(os, "environ", env)


@pytest.fixture
def mock_empty_env(mocker):
    mocker.patch.object(os, "environ", {})


@pytest.fixture
def mock_no_event_env(mocker, mock_bootstrap_servers, mock_producer_topic):

    env = {"KAFKA_BOOTSTRAP_SERVERS": mock_bootstrap_servers, "PRODUCER_TOPIC": mock_producer_topic}

    mocker.patch.object(os, "environ", env)


@pytest.fixture
def mock_no_producer_env(mocker, mock_bootstrap_servers, mock_benchmark_event):

    env = {"KAFKA_BOOTSTRAP_SERVERS": mock_bootstrap_servers, "BENCHMARK_EVENT": mock_benchmark_event}

    mocker.patch.object(os, "environ", env)


@pytest.fixture
def mock_no_bootstrap_servers_env(mocker, mock_producer_topic, mock_benchmark_event):

    env = {"PRODUCER_TOPIC": mock_producer_topic, "BENCHMARK_EVENT": mock_benchmark_event}

    mocker.patch.object(os, "environ", env)


@pytest.fixture
def mock_generate_uuid(mocker):
    return mocker.patch.object(__main__, "generate_uuid", side_effect=["new_uuid_1", "new_uuid_2"])


@pytest.fixture
def mock_kafka_producer():
    return MagicMock(spec=kafka.KafkaProducer)


@pytest.fixture
def mock_create_kafka_producer(mocker, mock_kafka_producer):
    return mocker.patch.object(__main__, "create_kafka_producer", return_value=mock_kafka_producer)


@pytest.fixture
def mock_fail_create_kafka_producer(mocker):
    return mocker.patch.object(__main__, "create_kafka_producer", side_effect=Exception("some error"))


@pytest.fixture
def mock_kafka_producer_send_failure(mocker, mock_kafka_producer):
    return mocker.patch.object(mock_kafka_producer, "send", return_value={})


def test_main(mock_create_kafka_producer, mock_kafka_producer, mock_generate_uuid, mock_env):
    """
    Test main happy path
    """
    from anubis_cron_job.__main__ import main

    main()

    # check kafka producer is created with the bootstrap servers
    mock_create_kafka_producer.assert_called_with(KAFKA_BOOTSTRAP_SERVERS)

    # check an event is sent
    mock_kafka_producer.send.assert_called()

    topic = mock_kafka_producer.send.call_args[0][0]
    event = mock_kafka_producer.send.call_args[1]["value"]
    key = mock_kafka_producer.send.call_args[1]["key"]

    # check event is sent to the right topic
    assert topic == PRODUCER_TOPIC

    # check new action and message ids are generated
    assert event.action_id == "new_uuid_1"
    assert event.message_id == "new_uuid_2"
    assert key == "19c104987141a846c0bbd688678c23fed19a5742"

    # check that the scheduling attribute is removed
    assert None is event.payload.toml.contents.get("info").get("scheduling", None)

    # check the kafka producer is closed
    mock_kafka_producer.close.assert_called()


@pytest_parametrize_plus(
    "env",
    [
        fixture_ref(mock_empty_env),
        fixture_ref(mock_no_bootstrap_servers_env),
        fixture_ref(mock_no_producer_env),
        fixture_ref(mock_no_event_env),
    ],
)
def test_config_error_exit(env):
    """
    Test main fails if the environment does not contain the required parameters
    """
    from anubis_cron_job.__main__ import main

    with pytest.raises(SystemExit):
        main()


@pytest_parametrize_plus(
    "failure", [fixture_ref(mock_fail_create_kafka_producer), fixture_ref(mock_kafka_producer_send_failure)]
)
def test_main_error_exit(failure, mock_env):
    """
    Test script exists when exceptions are thrown
    """
    from anubis_cron_job.__main__ import main

    with pytest.raises(SystemExit):
        main()
