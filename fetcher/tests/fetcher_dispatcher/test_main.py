from unittest.mock import patch

# Regression test
from bai_kafka_utils.kafka_service import KafkaServiceConfig
from fetcher_dispatcher import fetcher_dispatcher, args
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig

BOOTSTRAP_SERVERS = ["K1", "K2"]

S3_DATA_SET_BUCKET = "S3"

KUBECONFIG = "path/cfg"

LOGGING_LEVEL = "WARN"

FETCHER_JOB_IMAGE = "MYIMAGE"

ZOOKEEPER_ENSEMBLE_HOSTS = "Z1,Z2"

CONSUMER_TOPIC = "IN"

PRODUCER_TOPIC = "OUT"

BOOTSTRAP_SERVERS_ARG = ",".join(BOOTSTRAP_SERVERS)

DEFAULT_NAMESPACE = "default"

DEFAULT_RESTART_POLICY = "OnFailure"

STATUS_TOPIC = "STATUS"


@patch.object(args.os, "environ")
@patch.object(fetcher_dispatcher, "create_fetcher_dispatcher")
def test_main(mock_create_fetcher_dispatcher, mock):
    from fetcher_dispatcher.__main__ import main

    main(
        f"--consumer-topic {CONSUMER_TOPIC} "
        f"--producer-topic {PRODUCER_TOPIC} "
        f"--zookeeper-ensemble-hosts {ZOOKEEPER_ENSEMBLE_HOSTS} "
        f"--s3-data-set-bucket {S3_DATA_SET_BUCKET} "
        f"--bootstrap-servers {BOOTSTRAP_SERVERS_ARG} "
        f"--logging-level {LOGGING_LEVEL} "
        f"--fetcher-job-image {FETCHER_JOB_IMAGE} "
        f"--status-topic {STATUS_TOPIC}"
    )

    expected_common_kafka_cfg = KafkaServiceConfig(
        consumer_topic=CONSUMER_TOPIC,
        producer_topic=PRODUCER_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level=LOGGING_LEVEL,
        status_topic=STATUS_TOPIC,
    )

    fetcher_dispatcher_cfg = FetcherServiceConfig(
        zookeeper_ensemble_hosts=ZOOKEEPER_ENSEMBLE_HOSTS,
        s3_data_set_bucket=S3_DATA_SET_BUCKET,
        fetcher_job=FetcherJobConfig(
            image=FETCHER_JOB_IMAGE, namespace=DEFAULT_NAMESPACE, restart_policy=DEFAULT_RESTART_POLICY
        ),
    )

    mock_create_fetcher_dispatcher.assert_called_with(expected_common_kafka_cfg, fetcher_dispatcher_cfg)
