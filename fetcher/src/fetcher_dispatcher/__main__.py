import logging

from bai_kafka_utils.events import FetcherPayload
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaService, KafkaServiceConfig
from bai_kafka_utils.kafka_service_args import get_kafka_service_config
from fetcher_dispatcher import __version__, SERVICE_NAME, SERVICE_DESCRIPTION
from fetcher_dispatcher.args import get_fetcher_service_config, FetcherServiceConfig
from fetcher_dispatcher.fetcher_dispatcher import FetcherEventHandler, create_data_set_manager


def main(argv=None):
    common_kafka_cfg = get_kafka_service_config(SERVICE_NAME, argv)
    fetcher_cfg = get_fetcher_service_config(argv)

    logging.basicConfig(
        level=common_kafka_cfg.logging_level
    )

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info("common_args = %s", common_kafka_cfg)
    logger.info("fetcher_args = %s", fetcher_cfg)

    fetcher_service = create_fetcher_dispatcher(common_kafka_cfg, fetcher_cfg)
    fetcher_service.run_loop()


def create_fetcher_dispatcher(common_kafka_cfg: KafkaServiceConfig, fetcher_cfg: FetcherServiceConfig) -> KafkaService:
    data_set_mgr = create_data_set_manager(fetcher_cfg.zookeeper_ensemble_hosts,
                                           fetcher_cfg.kubeconfig,
                                           fetcher_cfg.fetcher_job_image, fetcher_cfg.fetcher_job_node_selector)
    data_set_mgr.start()

    callbacks = [
        FetcherEventHandler(data_set_mgr,
                            fetcher_cfg.s3_data_set_bucket)
    ]

    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, FetcherPayload)

    return KafkaService(SERVICE_NAME,
                        __version__,
                        common_kafka_cfg.producer_topic,
                        callbacks, consumer, producer)


if __name__ == '__main__':
    main()
