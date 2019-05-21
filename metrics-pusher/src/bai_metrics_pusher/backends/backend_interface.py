import abc

from typing import List, Union, Dict

AcceptedMetricTypes = Union[float, List[float]]


class Backend(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        """
        Emits the metrics to the backend.
        """
        pass

    @abc.abstractmethod
    def close(self):
        """
        Closes the backend.

        After calling this method, the object is unusable.
        """
        pass
