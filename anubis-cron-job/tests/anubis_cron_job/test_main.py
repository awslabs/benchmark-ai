import json
import os
from unittest.mock import MagicMock

import dacite
import kafka
import pytest
from bai_kafka_utils.events import FetcherBenchmarkEvent, Status
from bai_kafka_utils.executors.descriptor import SINGLE_RUN_SCHEDULING
from pytest_cases import pytest_parametrize_plus, fixture_ref

from anubis_cron_job import __main__
from anubis_cron_job.__main__ import create_benchmark_event

ACTION_ID = ""

BENCHMARK_EVENT = (
    '{"action_id": "@@ACTION_ID@@", "message_id":'
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
    '"python3 hello-world.py"}}, "doc": "something",'
    '"sha1": "6e38ce3d47171fbb387237e1c61e3feaba6c3b78", "descriptor_filename":'
    '"descriptor.toml", "verified": true}, "datasets": [], "scripts": []}}'
)

KAFKA_BOOTSTRAP_SERVERS = ["a", "b", "c"]
PRODUCER_TOPIC = "topic"
STATUS_TOPIC = "status"


@pytest.fixture
def mock_action_id():
    return ACTION_ID


@pytest.fixture
def mock_bootstrap_servers():
    return ",".join(KAFKA_BOOTSTRAP_SERVERS)


@pytest.fixture
def mock_benchmark_event(mock_action_id):
    return BENCHMARK_EVENT.replace("@@ACTION_ID@@", mock_action_id)


@pytest.fixture
def mock_producer_topic():
    return PRODUCER_TOPIC


@pytest.fixture
def mock_status_topic():
    return STATUS_TOPIC


@pytest.fixture
def mock_env(mock_bootstrap_servers, mock_producer_topic, mock_benchmark_event, mock_status_topic):
    return {
        "KAFKA_BOOTSTRAP_SERVERS": mock_bootstrap_servers,
        "PRODUCER_TOPIC": mock_producer_topic,
        "BENCHMARK_EVENT": mock_benchmark_event,
        "STATUS_TOPIC": mock_status_topic,
    }


@pytest.fixture
def mock_good_env(mocker, mock_env):
    mocker.patch.object(os, "environ", mock_env)


@pytest.fixture
def mock_empty_env(mocker):
    mocker.patch.object(os, "environ", {})


@pytest.fixture
def mock_no_event_env(mocker, mock_env):
    del mock_env["BENCHMARK_EVENT"]
    mocker.patch.object(os, "environ", mock_env)


@pytest.fixture
def mock_no_producer_env(mocker, mock_env):
    del mock_env["PRODUCER_TOPIC"]
    mocker.patch.object(os, "environ", mock_env)


@pytest.fixture
def mock_no_status_env(mocker, mock_env):
    del mock_env["STATUS_TOPIC"]
    mocker.patch.object(os, "environ", mock_env)


@pytest.fixture
def mock_no_bootstrap_servers_env(mocker, mock_env):
    del mock_env["KAFKA_BOOTSTRAP_SERVERS"]
    mocker.patch.object(os, "environ", mock_env)


@pytest.fixture
def mock_generate_uuid(mocker):
    return mocker.patch.object(__main__, "generate_uuid", side_effect=["new_uuid_1", "new_uuid_2", "new_uuid_3"])


@pytest.fixture
def mock_event_emitter(mocker):
    mock_emitter = mocker.patch("anubis_cron_job.__main__.EventEmitter", autospec=True)
    return mock_emitter.return_value


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


@pytest.fixture
def mock_scheduled_benchmark_event(mock_benchmark_event):
    return dacite.from_dict(data_class=FetcherBenchmarkEvent, data=json.loads(mock_benchmark_event))


def test_create_benchmark_event(mock_generate_uuid, mock_scheduled_benchmark_event):
    """
    Tests single run benchmark event is appropriately created from the scheduled benchmark event
    """
    event = create_benchmark_event(mock_scheduled_benchmark_event)

    assert event.action_id == "new_uuid_1"
    assert event.parent_action_id == mock_scheduled_benchmark_event.action_id
    assert event.payload.toml.contents["info"].get("scheduling") == SINGLE_RUN_SCHEDULING


def test_create_benchmark_event_fails_on_no_info(mock_scheduled_benchmark_event):
    """
    Test benchmark event creation fails if scheduled event does not have an 'info' section in the payload
    """
    # Remove info section
    mock_scheduled_benchmark_event.payload.toml.contents.pop("info")
    with pytest.raises(RuntimeError) as err:
        create_benchmark_event(mock_scheduled_benchmark_event)

    assert str(err.value) == "Event does not contain valid benchmark descriptor: 'info' section is missing."


def test_main(mock_create_kafka_producer, mock_event_emitter, mock_kafka_producer, mock_generate_uuid, mock_good_env):
    """
    Test main happy path
    """
    from anubis_cron_job.__main__ import main

    main()

    # check kafka producer is created with the bootstrap servers
    mock_create_kafka_producer.assert_called_with(KAFKA_BOOTSTRAP_SERVERS)

    # check an event is sent correctly
    mock_event_emitter.send_event.assert_called_once()

    topic = mock_event_emitter.send_event.call_args[1]["topic"]
    event = mock_event_emitter.send_event.call_args[1]["event"]
    assert topic == PRODUCER_TOPIC
    assert event.action_id == "new_uuid_1"

    # check status event is sent correctly
    mock_event_emitter.send_status_message_event.assert_called_once()

    event = mock_event_emitter.send_status_message_event.call_args[1]["handled_event"]
    status = mock_event_emitter.send_status_message_event.call_args[1]["status"]

    # check action id from scheduled benchmark is used
    assert event.action_id == ACTION_ID
    assert status == Status.SUCCEEDED

    # check the kafka producer is closed
    mock_kafka_producer.close.assert_called()


@pytest_parametrize_plus(
    "env",
    [
        fixture_ref(mock_empty_env),
        fixture_ref(mock_no_bootstrap_servers_env),
        fixture_ref(mock_no_producer_env),
        fixture_ref(mock_no_event_env),
        fixture_ref(mock_no_status_env),
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
