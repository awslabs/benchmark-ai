from .FilePublisher import FilePublisher


class MetricsFactory:
    def __init__(self, publishers=None):
        if publishers is None:
            publishers = []
        self.publishers = publishers

    def emit(self, metrics_dict):
        for p in self.publishers:
            p.publish(metrics_dict)

    def register_publisher(self, publisher):
        self.publishers.append(publisher)

    def unregister_publisher(self, publisher):
        self.publishers.remove(publisher)

    @staticmethod
    def create_default():
        return MetricsFactory([FilePublisher()])

    __instance = None

    @staticmethod
    def default():
        if not MetricsFactory.__instance:
            MetricsFactory.__instance = MetricsFactory.create_default()
        return MetricsFactory.__instance


def emit(metrics_dict):
    MetricsFactory.default().emit(metrics_dict)
