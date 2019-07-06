from unittest import mock

from transpiler.config import BaiConfig, EnvironmentInfo, AvailabilityZoneInfo
from transpiler.descriptor import DescriptorConfig
from bai_kafka_utils.kafka_service import KafkaServiceConfig, DEFAULT_NUM_PARTITIONS, DEFAULT_REPLICATION_FACTOR
from executor.config import ExecutorConfig


BOOTSTRAP_SERVERS = ["K1", "K2"]
KUBECTL = "path/cfg"
LOGGING_LEVEL = "WARN"
CONSUMER_TOPIC = "IN"
PRODUCER_TOPIC = "OUT"
CMD_SUBMIT_TOPIC = "CMD_SUBMIT"
CMD_RETURN_TOPIC = "CMD_RETURN"
STATUS_TOPIC = "STATUS_TOPIC"
BOOTSTRAP_SERVERS_ARG = ",".join(BOOTSTRAP_SERVERS)
VALID_STRATEGIES = "s1,s2"
PULLER_MOUNT_CHMOD = "700"
PULLER_S3_REGION = "us-east-1"
PULLER_DOCKER_IMAGE = "example/docker:img"
AVAILABILITY_ZONES_NAMES = "az1,az2,az3"
AVAILABILITY_ZONES_IDS = "az-id1,az-id2,az-id3"

EXPECTED_AVAILABILITY_ZONES = [
    AvailabilityZoneInfo("az1", "az-id1"),
    AvailabilityZoneInfo("az2", "az-id2"),
    AvailabilityZoneInfo("az3", "az-id3"),
]


@mock.patch("executor.executor.create_executor")
def test_main(mock_create_executor):
    from executor.__main__ import main

    main(
        f" --consumer-topic {CONSUMER_TOPIC} "
        f" --producer-topic {PRODUCER_TOPIC} "
        f" --cmd-submit-topic {CMD_SUBMIT_TOPIC}"
        f" --cmd-return-topic {CMD_RETURN_TOPIC}"
        f" --status-topic {STATUS_TOPIC} "
        f" --bootstrap-servers {BOOTSTRAP_SERVERS_ARG} "
        f" --logging-level {LOGGING_LEVEL} "
        f" --kubectl {KUBECTL} "
        f" --transpiler-valid-strategies {VALID_STRATEGIES} "
        f" --transpiler-puller-mount-chmod {PULLER_MOUNT_CHMOD} "
        f" --transpiler-puller-s3-region {PULLER_S3_REGION} "
        f" --transpiler-puller-docker-image {PULLER_DOCKER_IMAGE} "
        f" --availability-zones-names {AVAILABILITY_ZONES_NAMES} "
        f" --availability-zones-ids {AVAILABILITY_ZONES_IDS} "
    )

    expected_common_kafka_cfg = KafkaServiceConfig(
        consumer_topic=CONSUMER_TOPIC,
        producer_topic=PRODUCER_TOPIC,
        cmd_submit_topic=CMD_SUBMIT_TOPIC,
        cmd_return_topic=CMD_RETURN_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        logging_level=LOGGING_LEVEL,
        status_topic=STATUS_TOPIC,
        replication_factor=min(DEFAULT_REPLICATION_FACTOR, len(BOOTSTRAP_SERVERS)),
        num_partitions=DEFAULT_NUM_PARTITIONS,
    )

    expected_executor_config = ExecutorConfig(
        kubectl=KUBECTL,
        descriptor_config=DescriptorConfig(valid_strategies=VALID_STRATEGIES.split(",")),
        bai_config=BaiConfig(
            puller_s3_region=PULLER_S3_REGION,
            puller_mount_chmod=PULLER_MOUNT_CHMOD,
            puller_docker_image=PULLER_DOCKER_IMAGE,
        ),
        environment_info=EnvironmentInfo(availability_zones=EXPECTED_AVAILABILITY_ZONES),
    )

    mock_create_executor.assert_called_with(expected_common_kafka_cfg, expected_executor_config)
