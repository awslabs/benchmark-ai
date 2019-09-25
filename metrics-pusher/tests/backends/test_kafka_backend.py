import datetime
import pytest

from unittest.mock import call, create_autospec

import kafka

from bai_metrics_pusher.backends.kafka_backend import KafkaBackend, KafkaExporterMetric


@pytest.fixture
def mock_kafka_producer(mocker):
    mock_kafka_producer = create_autospec(kafka.KafkaProducer)
    mocker.patch.object(kafka, "KafkaProducer", return_value=mock_kafka_producer)
    return mock_kafka_producer


@pytest.fixture(autouse=True)
def freeze_time_to_1_second_after_epoch(mocker):
    # Can't use `freezegun` because it removes the timezone information from the frozen time.
    # https://github.com/spulec/freezegun/issues/89
    mock_datetime = mocker.patch("datetime.datetime")
    mock_datetime.utcnow.return_value = datetime.datetime(1970, 1, 1, 0, 0, second=1, tzinfo=datetime.timezone.utc)
    yield


def test_1_metric(mock_kafka_producer):
    kafka_backend = KafkaBackend("action-id", "client-id", topic="KAFKA_TOPIC", key="KAFKA_KEY")

    kafka_backend.emit({"metric": 0.1})

    expected_metric_object = KafkaExporterMetric(
        name="metric", value=0.1, timestamp=1000, labels={"action-id": "action-id", "client-id": "client-id"}
    )
    assert mock_kafka_producer.send.call_args_list == [
        call("KAFKA_TOPIC", value=expected_metric_object, key="KAFKA_KEY")
    ]


def test_2_metrics(mock_kafka_producer):
    kafka_backend = KafkaBackend("action-id", "client-id", topic="KAFKA_TOPIC", key="KAFKA_KEY")
    kafka_backend.emit({"metric1": 0.1, "metric2": 0.2})

    expected_metric_object1 = KafkaExporterMetric(
        name="metric1", value=0.1, timestamp=1000, labels={"action-id": "action-id", "client-id": "client-id"}
    )
    expected_metric_object2 = KafkaExporterMetric(
        name="metric2", value=0.2, timestamp=1000, labels={"action-id": "action-id", "client-id": "client-id"}
    )
    assert mock_kafka_producer.send.call_args_list == [
        call("KAFKA_TOPIC", value=expected_metric_object1, key="KAFKA_KEY"),
        call("KAFKA_TOPIC", value=expected_metric_object2, key="KAFKA_KEY"),
    ]


def test_close(mock_kafka_producer):
    kafka_backend = KafkaBackend("action-id", "client-id", topic="KAFKA_TOPIC", key="KAFKA_KEY")
    kafka_backend.close()
    assert mock_kafka_producer.close.call_args_list == [call()]
