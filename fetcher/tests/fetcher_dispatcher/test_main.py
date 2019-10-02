from unittest.mock import patch

# Regression test
from bai_kafka_utils.kafka_service import KafkaServiceConfig, DEFAULT_NUM_PARTITIONS, DEFAULT_REPLICATION_FACTOR
from fetcher_dispatcher import fetcher_dispatcher_service, args
from fetcher_dispatcher.args import FetcherServiceConfig, FetcherJobConfig, FetcherVolumeConfig

BOOTSTRAP_SERVERS = ["K1", "K2"]

S3_DOWNLOAD_BUCKET = "S3"

KUBECONFIG = "path/cfg"

LOGGING_LEVEL = "WARN"

FETCHER_JOB_IMAGE = "MYIMAGE"

ZOOKEEPER_ENSEMBLE_HOSTS = "Z1,Z2"

CONSUMER_TOPIC = "IN"

PRODUCER_TOPIC = "OUT"

CMD_RETURN_TOPIC = "CMD_RETURN"

CMD_SUBMIT_TOPIC = "CMD_SUBMIT"

BOOTSTRAP_SERVERS_ARG = ",".join(BOOTSTRAP_SERVERS)

DEFAULT_NAMESPACE = "default"

DEFAULT_RESTART_POLICY = "OnFailure"

STATUS_TOPIC = "STATUS"

MIN_VOLUME_SIZE = 256


@patch.object(args.os, "environ", autospec=True)
@patch.object(fetcher_dispatcher_service, "create_fetcher_dispatcher", autospec=True)
def test_main(mock_create_fetcher_dispatcher, mock):
    from fetcher_dispatcher.__main__ import main

    main(
        f"--consumer-topic {CONSUMER_TOPIC} "
        f"--producer-topic {PRODUCER_TOPIC} "
        f"--zookeeper-ensemble-hosts {ZOOKEEPER_ENSEMBLE_HOSTS} "
        f"--s3-download-bucket {S3_DOWNLOAD_BUCKET} "
        f"--bootstrap-servers {BOOTSTRAP_SERVERS_ARG} "
        f"--logging-level {LOGGING_LEVEL} "
        f"--fetcher-job-image {FETCHER_JOB_IMAGE} "
        f"--status-topic {STATUS_TOPIC} "
        f"--cmd-return-topic {CMD_RETURN_TOPIC} "
        f"--cmd-submit-topic {CMD_SUBMIT_TOPIC} "
        f"--fetcher-job-min-volume-size {MIN_VOLUME_SIZE}"
    )

    expected_common_kafka_cfg = KafkaServiceConfig(
        consumer_topic=CONSUMER_TOPIC,
        producer_topic=PRODUCER_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level=LOGGING_LEVEL,
        status_topic=STATUS_TOPIC,
        cmd_return_topic=CMD_RETURN_TOPIC,
        cmd_submit_topic=CMD_SUBMIT_TOPIC,
        replication_factor=min(DEFAULT_REPLICATION_FACTOR, len(BOOTSTRAP_SERVERS)),
        num_partitions=DEFAULT_NUM_PARTITIONS,
    )

    fetcher_dispatcher_cfg = FetcherServiceConfig(
        zookeeper_ensemble_hosts=ZOOKEEPER_ENSEMBLE_HOSTS,
        s3_download_bucket=S3_DOWNLOAD_BUCKET,
        fetcher_job=FetcherJobConfig(
            image=FETCHER_JOB_IMAGE,
            namespace=DEFAULT_NAMESPACE,
            restart_policy=DEFAULT_RESTART_POLICY,
            volume=FetcherVolumeConfig(min_size=MIN_VOLUME_SIZE),
        ),
    )

    mock_create_fetcher_dispatcher.assert_called_with(expected_common_kafka_cfg, fetcher_dispatcher_cfg)
