from kafka import KafkaConsumer, KafkaProducer
from unittest.mock import patch, MagicMock

from bai_kafka_utils import kafka_client
from bai_kafka_utils.kafka_service_args import CONSUMER_TOPIC_ARG, PRODUCER_TOPIC_ARG, CONSUMER_GROUP_ID_ARG
from fetcher_dispatcher import fetcher_dispatcher
from fetcher_dispatcher.args import get_args, FETCHER_JOB_IMAGE_ARG, S3_DATA_SET_BUCKET_ARG, KUBECONFIG_ARG, \
    ZOOKEEPER_ENSEMBLE_HOSTS_ARG, FETCHER_JOB_NODE_SELECTOR_ARG
from fetcher_dispatcher.data_set_manager import DataSetManager

MOCK_S3_BUCKET = "s3://something"

MOCK_NODE_SELECTOR = {"node.type": "foo"}

MOCK_DOCKER_IMAGE = "docker/image"

MOCK_ZOOKEEPER_ENSEMBLE = "ZE1,ZE2"

MOCK_KUBECONFIG = "/path/kubeconfig"

REQUIRED_ARGS = f"{CONSUMER_TOPIC_ARG} C {PRODUCER_TOPIC_ARG} P {S3_DATA_SET_BUCKET_ARG} {MOCK_S3_BUCKET} " \
                    f"{FETCHER_JOB_IMAGE_ARG}={MOCK_DOCKER_IMAGE} " + \
                f"{ZOOKEEPER_ENSEMBLE_HOSTS_ARG}={MOCK_ZOOKEEPER_ENSEMBLE} {KUBECONFIG_ARG} {MOCK_KUBECONFIG}"

ALL_ARGS = REQUIRED_ARGS + f" {FETCHER_JOB_NODE_SELECTOR_ARG}=" + '{"node.type":"foo"} ' + f"{CONSUMER_GROUP_ID_ARG} CG"


def test_json_arg():
    args = get_args(ALL_ARGS)
    assert args.fetcher_job_node_selector == MOCK_NODE_SELECTOR


@patch.object(fetcher_dispatcher, "FetcherEventHandler")
@patch.object(kafka_client, "create_kafka_consumer_producer")
@patch.object(fetcher_dispatcher, "create_data_set_manager")
def test_args_names_match_attributes(mock_create_data_set_manager, mock_create_kafka_consumer_producer,
                                     mockFetcherEventHandler):
    args = get_args(ALL_ARGS)

    # Import locally to patch properly
    from fetcher_dispatcher.__main__ import create_fetcher_dispatcher

    # Common Kafka args are tested in bai_kafka_utils
    mock_create_kafka_consumer_producer.return_value = (MagicMock(spec=KafkaConsumer),
                                                        MagicMock(spec=KafkaProducer))

    mock_data_set = MagicMock(spec=DataSetManager)
    mock_create_data_set_manager.return_value = mock_data_set

    create_fetcher_dispatcher(args)

    mock_create_data_set_manager.assert_called_with(MOCK_ZOOKEEPER_ENSEMBLE, MOCK_KUBECONFIG, MOCK_DOCKER_IMAGE,
                                                    MOCK_NODE_SELECTOR)
    mockFetcherEventHandler.assert_called_with(mock_data_set, MOCK_S3_BUCKET)
