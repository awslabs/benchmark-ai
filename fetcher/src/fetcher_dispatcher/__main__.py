import logging

from bai_kafka_utils.events import FetcherPayload
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaService
from fetcher_dispatcher import __version__, SERVICE_NAME, SERVICE_DESCRIPTION
from fetcher_dispatcher.args import get_args
from fetcher_dispatcher.fetcher_dispatcher import FetcherEventHandler, create_data_set_manager


def main(argv=None):
    args = get_args(argv)

    logging.basicConfig(
        level=args.logging_level
    )

    logger = logging.getLogger(SERVICE_NAME)
    logger.info(f"Starting {SERVICE_NAME} Service: {SERVICE_DESCRIPTION}")
    logger.info("args = %s", args)

    fetcher_service = create_fetcher_dispatcher(args)
    fetcher_service.run_loop()


def create_fetcher_dispatcher(args) -> KafkaService:
    data_set_mgr = create_data_set_manager(args.zookeeper_ensemble_hosts,
                                           args.kubeconfig,
                                           args.fetcher_job_image, args.fetcher_job_node_selector)
    data_set_mgr.start()

    callbacks = [
        FetcherEventHandler(data_set_mgr,
                            args.s3_data_set_bucket)
    ]

    consumer, producer = create_kafka_consumer_producer(args, FetcherPayload)

    return KafkaService(SERVICE_NAME,
                        __version__,
                        args.producer_topic,
                        callbacks, consumer, producer)


if __name__ == '__main__':
    main()
