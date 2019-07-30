import bai_kafka_utils
from bai_kafka_utils.executors.execution_callback import ExecutionEngine
from bai_kafka_utils.executors.executor_service import create_executor_service
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from kafka import KafkaConsumer, KafkaProducer
from pytest import fixture
from unittest.mock import MagicMock, create_autospec

EXECUTION_ENGINES = {"SOME_ENGINE": create_autospec(ExecutionEngine)}

VERSION = "1.0"

SERVICE_NAME = "some-service"


@fixture
def mock_create_consumer_producer(mocker):
    mock_consumer = MagicMock(spec=KafkaConsumer)
    mock_producer = MagicMock(spec=KafkaProducer)
    mock_create_consumer_producer = mocker.patch.object(
        bai_kafka_utils.executors.executor_service,
        "create_kafka_consumer_producer",
        return_value=(mock_consumer, mock_producer),
        autospec=True,
    )
    return mock_create_consumer_producer


def test_create_executor(mock_create_consumer_producer, kafka_service_config: KafkaServiceConfig):
    executor = create_executor_service(SERVICE_NAME, VERSION, kafka_service_config, EXECUTION_ENGINES)

    mock_create_consumer_producer.assert_called_once()

    assert isinstance(executor, KafkaService)
    assert kafka_service_config.consumer_topic in executor._callbacks
    assert kafka_service_config.cmd_submit_topic in executor._callbacks
