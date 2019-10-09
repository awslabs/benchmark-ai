import abc
import itertools
import time
from threading import Thread
from typing import Callable, Tuple, Optional

from bai_watcher import service_logger
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

SLEEP_TIME_BETWEEN_CHECKS_SECONDS = 5

logger = service_logger.getChild(__name__)


class AbstractJobWatcherBase(metaclass=abc.ABCMeta):
    pass


JobWatcherCallback = Callable[[str, BenchmarkJobStatus, AbstractJobWatcherBase], bool]


class JobWatcher(AbstractJobWatcherBase):
    def __init__(
        self, job_id: str, callback: JobWatcherCallback, period_seconds: int = SLEEP_TIME_BETWEEN_CHECKS_SECONDS
    ):
        self._job_id = job_id
        self._callback = callback
        self._thread = Thread(target=self._thread_run_loop, daemon=True, name=f"k8s-job-watcher-{job_id}")
        self._error = None
        self._success = None
        self._period_seconds = period_seconds

    @abc.abstractmethod
    def _get_status(self):
        pass

    def start(self):
        self._thread.start()

    def wait(self):
        self._thread.join()

    def get_result(self) -> Tuple[Optional[bool], Optional[Exception]]:
        return self._success, self._error

    def _thread_run_loop(self):
        # Use itertools.count() so that tests can mock the infinite loop
        for _ in itertools.count():
            try:
                status = self._get_status()
                stop_watching = self._callback(self._job_id, status, self)
                if stop_watching:
                    self._success = True
                    return
            except Exception as err:
                logger.exception("Watcher loop failed with uncaught exception")
                self._success = False
                self._error = err
                return
            time.sleep(self._period_seconds)
