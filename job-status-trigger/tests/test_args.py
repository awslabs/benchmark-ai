import pytest

from bai_job_status_trigger.args import JobStatusTriggerConfig, get_job_status_trigger_config
from bai_watcher.status_inferrers.status import BenchmarkJobStatus

JOB_NAMESPACE = "namespace"
JOB_NAME = "job_name"
TRIGGER_STATUSES = "SUCCEEDED, FAILED"
JOB_NOT_FOUND_GRACE_PERIOD_SECONDS = 30
COMMAND = "command"

MOST_ARGS = (
    f" --job-namespace={JOB_NAMESPACE}"
    f" --job-name={JOB_NAME} "
    f" --job-not-found-grace-period-seconds={JOB_NOT_FOUND_GRACE_PERIOD_SECONDS}"
    f" --command={COMMAND}"
)


@pytest.mark.parametrize(
    "statuses,expected_statuses",
    [
        ("SUCCEEDED, FAILED", [BenchmarkJobStatus.SUCCEEDED, BenchmarkJobStatus.FAILED]),
        ("SUCCEEDED FAILED", [BenchmarkJobStatus.SUCCEEDED, BenchmarkJobStatus.FAILED]),
        ("SUCCEEDED", [BenchmarkJobStatus.SUCCEEDED]),
    ],
)
def test_get_job_status_trigger_config(statuses, expected_statuses):
    expected_cfg = JobStatusTriggerConfig(
        job_namespace=JOB_NAMESPACE,
        job_name=JOB_NAME,
        trigger_statuses=expected_statuses,
        job_not_found_grace_period_seconds=JOB_NOT_FOUND_GRACE_PERIOD_SECONDS,
        command=COMMAND,
    )
    cfg = get_job_status_trigger_config(MOST_ARGS + f" --trigger-statuses={statuses}")
    assert cfg == expected_cfg


def test_dont_fail_unrecognized():
    get_job_status_trigger_config(MOST_ARGS + f" --trigger-statuses=SUCCEEDED" + " -foo")
