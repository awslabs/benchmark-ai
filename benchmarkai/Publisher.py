import abc


class Publisher:
    @abc.abstractmethod
    def publish(self, metrics_dict):
        ...
