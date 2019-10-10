from typing import Callable
from unittest.mock import call

from pytest import fixture

from bai_watcher.job_watcher import JobWatcher, JobWatcherCallback, SLEEP_TIME_BETWEEN_CHECKS_SECONDS
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

GetStatusFn = Callable[[], BenchmarkJobStatus]


@fixture
def true_callback() -> JobWatcherCallback:
    def callback(job_id: str, status: BenchmarkJobStatus):
        return True

    return callback


@fixture
def false_callback() -> JobWatcherCallback:
    def callback(job_id: str, status: BenchmarkJobStatus):
        return False

    return callback


def make_mock_job_watcher(get_status: GetStatusFn, job_id: str, callback: JobWatcherCallback):
    class MockJobWatcher(JobWatcher):
        def _get_status(self):
            return get_status()

    return MockJobWatcher(job_id=job_id, callback=callback)


def make_get_status_fn(status_to_return: BenchmarkJobStatus) -> GetStatusFn:
    def fn() -> BenchmarkJobStatus:
        return status_to_return

    return fn


def mock_loop_dependencies(mocker, *, iterations):
    mocker.patch("itertools.count", return_value=[0] * iterations)
    mock_time_sleep = mocker.patch("time.sleep")
    return mock_time_sleep


def test_stops_watching_when_callback_is_true(mocker, true_callback):
    mock_sleep = mock_loop_dependencies(mocker, iterations=1)
    status_fn = make_get_status_fn(status_to_return=BenchmarkJobStatus.SUCCEEDED)
    watcher = make_mock_job_watcher(job_id="id", callback=true_callback, get_status=status_fn)
    watcher.start()
    watcher.wait()
    mock_sleep.assert_not_called()
    assert watcher.get_result() == (True, None)


def test_continues_watching_when_callback_is_false(mocker, false_callback):
    mock_sleep = mock_loop_dependencies(mocker, iterations=5)
    status_fn = make_get_status_fn(status_to_return=BenchmarkJobStatus.SUCCEEDED)
    watcher = make_mock_job_watcher(job_id="id", callback=false_callback, get_status=status_fn)
    watcher.start()

    # iterations is set to 5 in mock setup
    assert mock_sleep.call_args_list == [call(SLEEP_TIME_BETWEEN_CHECKS_SECONDS)] * 5


def test_stops_watching_when_get_status_raises(mocker, true_callback):
    mock_sleep = mock_loop_dependencies(mocker, iterations=1)

    err = RuntimeError("Something bad happened")

    def status_fn() -> BenchmarkJobStatus:
        raise err

    watcher = make_mock_job_watcher(job_id="id", callback=true_callback, get_status=status_fn)
    watcher.start()
    watcher.wait()
    mock_sleep.assert_not_called()
    assert watcher.get_result() == (False, err)
