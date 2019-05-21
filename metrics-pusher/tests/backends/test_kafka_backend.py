import datetime
import pytest

from unittest.mock import call, Mock

import kafka

from bai_metrics_pusher.backends.kafka_backend import KafkaBackend, KafkaExporterMetric


@pytest.fixture
def mock_kafka_producer_send(mocker):
    mock_kafka_producer_class = mocker.patch.object(kafka, "KafkaProducer")
    mock_kafka_producer = Mock(spec=kafka.KafkaProducer, autospec=True)
    mock_kafka_producer.send = Mock()
    mock_kafka_producer_class.return_value = mock_kafka_producer
    return mock_kafka_producer.send


@pytest.fixture(autouse=True)
def freeze_time_to_1_second_after_epoch(mocker):
    # Can't use `freezegun` because it removes the timezone information from the frozen time.
    # https://github.com/spulec/freezegun/issues/89
    mock_datetime = mocker.patch("datetime.datetime")
    mock_datetime.utcnow.return_value = datetime.datetime(1970, 1, 1, 0, 0, second=1, tzinfo=datetime.timezone.utc)
    yield


def test_1_metric(mock_kafka_producer_send):
    kafka_backend = KafkaBackend("job-id", topic="KAFKA_TOPIC", key="KAFKA_KEY")

    kafka_backend({"metric": 0.1})

    expected_metric_object = KafkaExporterMetric(
        name="metric", value=0.1, timestamp=1000, labels={"job-id": "job-id", "sender": "metrics-pusher"}
    )
    assert mock_kafka_producer_send.call_args_list == [
        call("KAFKA_TOPIC", value=expected_metric_object, key="KAFKA_KEY")
    ]


def test_2_metrics(mock_kafka_producer_send):
    kafka_backend = KafkaBackend("job-id", topic="KAFKA_TOPIC", key="KAFKA_KEY")
    kafka_backend({"metric1": 0.1, "metric2": 0.2})

    expected_metric_object1 = KafkaExporterMetric(
        name="metric1", value=0.1, timestamp=1000, labels={"job-id": "job-id", "sender": "metrics-pusher"}
    )
    expected_metric_object2 = KafkaExporterMetric(
        name="metric2", value=0.1, timestamp=1000, labels={"job-id": "job-id", "sender": "metrics-pusher"}
    )
    mock_kafka_producer_send.call_args_list == [
        call("KAFKA_TOPIC", value=expected_metric_object1, key="KAFKA_KEY"),
        call("KAFKA_TOPIC", value=expected_metric_object2, key="KAFKA_KEY"),
    ]
