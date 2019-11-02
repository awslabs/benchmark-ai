#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import abc
import itertools
import time
from threading import Thread
from typing import Callable, Tuple, Optional

from bai_watcher import service_logger
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

SLEEP_TIME_BETWEEN_CHECKS_SECONDS = 5

logger = service_logger.getChild(__name__)


JobWatcherCallback = Callable[[str, BenchmarkJobStatus], bool]


class JobWatcher(metaclass=abc.ABCMeta):
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
                stop_watching = self._callback(self._job_id, status)
                if stop_watching:
                    self._success = True
                    return
            except Exception as err:
                logger.exception("Watcher loop failed with uncaught exception")
                self._success = False
                self._error = err
                return
            time.sleep(self._period_seconds)
