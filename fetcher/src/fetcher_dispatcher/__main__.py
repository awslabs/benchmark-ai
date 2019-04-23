import logging

from fetcher_dispatcher import __version__, SERVICE_NAME, SERVICE_DESCRIPTION
from fetcher_dispatcher.fetcher_dispatcher import FetcherEventHandler, FetcherCleanupHandler, create_data_set_manager
from bai_kafka_utils.kafka_service import create_kafka_service_parser, KafkaService
from bai_kafka_utils.events import FetcherPayload


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


def get_args(args):
    parser = create_kafka_service_parser(SERVICE_NAME)

    parser.add_argument("--zookeeper-ensemble-hosts",
                        env_var="ZOOKEEPER_ENSEMBLE_HOSTS",
                        default="localhost:2181")

    parser.add_argument("--s3-data-set-bucket",
                        env_var="S3_DATASET_BUCKET",
                        required=True)

    parser.add_argument("--kubeconfig",
                        env_var="KUBECONFIG")

    parser.add_argument("--fetcher-job-image",
                        env_var="FETCHER_JOB_IMAGE")

    parsed_args = parser.parse_args(args)
    return parsed_args


def create_fetcher_dispatcher(args) -> KafkaService:
    data_set_mgr = create_data_set_manager(args.zookeeper_ensemble_hosts,
                                           args.kubeconfig,
                                           args.fetcher_job_image)
    data_set_mgr.start()

    callbacks = [
        FetcherEventHandler(data_set_mgr,
                            args.s3_data_set_bucket)
    ]

    return KafkaService(SERVICE_NAME,
                        __version__,
                        FetcherPayload,
                        args,
                        callbacks)


if __name__ == '__main__':
    main()
