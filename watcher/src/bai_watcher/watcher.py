from bai_kafka_utils.events import BenchmarkEvent, ExecutorPayload
from bai_kafka_utils.kafka_client import create_kafka_consumer_producer
from bai_kafka_utils.kafka_service import KafkaServiceCallback, KafkaService, KafkaServiceConfig
from bai_watcher import SERVICE_NAME, __version__
from bai_watcher.args import WatcherServiceConfig


class HelloEventHandler(KafkaServiceCallback):
    def handle_event(self, event: BenchmarkEvent, kafka_service: KafkaService):
        print(f"Got event: {event}, from service: {kafka_service}")

    def cleanup(self):
        pass


def create_service(common_kafka_cfg: KafkaServiceConfig, service_cfg: WatcherServiceConfig) -> KafkaService:
    callbacks = [HelloEventHandler()]
    consumer, producer = create_kafka_consumer_producer(common_kafka_cfg, ExecutorPayload)
    return KafkaService(SERVICE_NAME, __version__, common_kafka_cfg.producer_topic, callbacks, consumer, producer)
