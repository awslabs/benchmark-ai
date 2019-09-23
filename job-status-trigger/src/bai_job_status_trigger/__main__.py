#!/usr/bin/env python
import kubernetes
import os
import sys

from time import time

from subprocess import check_output
from typing import Callable, List

from kubernetes.client import ApiClient, BatchV1Api, CoreV1Api

from bai_kafka_utils.logging import configure_logging
from bai_job_status_trigger import app_logger
from bai_job_status_trigger.args import get_job_status_trigger_config, JobStatusTriggerConfig
from bai_watcher.kubernetes_job_watcher import KubernetesJobWatcher, load_kubernetes_config
from bai_watcher.status_inferrers.status import BenchmarkJobStatus


logger = app_logger.getChild(__name__)


def get_kubernetes_api_clients() -> (CoreV1Api, BatchV1Api):
    logger.info("Creating Kubernetes api clients")
    load_kubernetes_config(os.environ.get("KUBECONFIG", None))
    api_client = ApiClient(kubernetes.client.Configuration())
    return CoreV1Api(api_client=api_client), BatchV1Api(api_client=api_client)


def make_trigger_callback(
    trigger_statuses: List[BenchmarkJobStatus], not_found_grace_period_seconds: int
) -> Callable[[str, BenchmarkJobStatus, KubernetesJobWatcher], bool]:
    job_seen = False
    start_time = int(time())

    def status_trigger_callback(job_name: str, job_status: BenchmarkJobStatus, watcher: KubernetesJobWatcher) -> bool:
        nonlocal job_seen

        # For the first job_not_found_grace_period_seconds seconds, ignore not found
        if job_status == BenchmarkJobStatus.JOB_NOT_FOUND:
            elapsed = int(time() - start_time)

            # job has not been seen before grace period elapsed
            if not job_seen and elapsed >= not_found_grace_period_seconds:
                raise RuntimeError(f"Could not find job within {not_found_grace_period_seconds} seconds")

            # job has been seen before, but has disappeared
            if job_seen and BenchmarkJobStatus.JOB_NOT_FOUND not in trigger_statuses:
                raise RuntimeError(f"Job {job_name} could no longer be found")
        else:
            job_seen = True

        # Trigger action if job has been seen and meets status criteria
        if job_status in trigger_statuses and job_seen:
            logger.info(f"Job status is {job_status} - executing trigger")
            return True
        logger.info(f"Job {job_name}: {job_status}")
        return False

    return status_trigger_callback


def main():
    configure_logging(level=os.environ.get("LOGGING_LEVEL", "INFO").upper())
    config: JobStatusTriggerConfig = get_job_status_trigger_config(sys.argv)
    core_v1api, batch_v1api = get_kubernetes_api_clients()

    logger.info(f"Executing Job Status Trigger w/ Configuration: {config}")

    job_watcher = KubernetesJobWatcher(
        job_id=config.job_name,
        callback=make_trigger_callback(config.trigger_statuses, config.job_not_found_grace_period_seconds),
        kubernetes_namespace=config.job_namespace,
        kubernetes_client_jobs=batch_v1api,
        kubernetes_client_pods=core_v1api,
    )

    job_watcher.start()

    # block until execution is complete
    job_watcher.wait()

    success, err = job_watcher.get_result()

    if success:
        logger.info(check_output(["bash", "-c", config.command]))
    else:
        logger.exception("Job status watcher failed", err)
        sys.exit(1)


if __name__ == "__main__":
    main()
