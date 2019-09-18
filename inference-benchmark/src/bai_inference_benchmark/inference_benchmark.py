import itertools
import logging
import os
import time
from enum import Enum, unique
from pathlib import Path
from typing import Optional

import kubernetes
import yaml
from kubernetes.client import ApiClient, CoreV1Api, V1Pod
from kubernetes.client.rest import ApiException

from bai_inference_benchmark import app_logger
from bai_inference_benchmark.args import InferenceBenchmarkConfig

logger = app_logger.getChild(__name__)


class InferenceBenchmarkFailedError(Exception):
    pass


@unique
class PodStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RUNNING = "running"
    UNKNOWN = "unknown"
    NOT_FOUND = "not found"

    def is_final(self):
        return self in (PodStatus.SUCCEEDED, PodStatus.FAILED, PodStatus.UNKNOWN)

    def is_successful(self):
        return self in (PodStatus.SUCCEEDED,)

    def __str__(self):
        return self.value.title()


class InferenceBenchmark:

    SLEEP_TIME = 5

    @staticmethod
    def _create_api_client_instance() -> ApiClient:
        """
        Creates a new Kubernetes API client.
        Will attempt to load the client configuration from $KUBECONFIG,
        or ~/.kube/config, if it's not set. If not kubeconfig file is found,
        load_incluster_config will be executed.
        :return: A kubernetes.ApiClient instance configured against the current
        execution environment.
        """
        kubeconfig_path = os.environ.get("KUBECONFIG", Path.home().joinpath(".kube", "config"))
        kubeconfig = Path(kubeconfig_path)

        if kubeconfig.exists():
            logger.info(f"Loading kubeconfig from {kubeconfig_path}")
            kubernetes.config.load_kube_config(str(kubeconfig))
        else:
            logger.info(f"Loading kubeconfig from in the cluster")
            kubernetes.config.load_incluster_config()

        return ApiClient(kubernetes.client.Configuration())

    def __init__(self, config: InferenceBenchmarkConfig):
        self._namespace = config.benchmark_namespace
        self._benchmark_pod_spec = config.benchmark_pod_spec
        self._server_pod_spec = config.server_pod_spec

        self._api_client = self._create_api_client_instance()
        self._corev1_api = CoreV1Api(api_client=self._api_client)

    def _create_pod(self, namespace: str, pod_spec: Path):
        """
        Creates a pod defined by the pod_spec in the specified namespace.
        :param namespace: Namespace to start pod in
        :param pod_spec: Path to Pod Spec yaml file
        :return: The name of the pod
        :raises ApiException: When there is an error calling the Kubernetes API
        :raises FileNotFoundError: If the Pod Spec yaml file could not be found
        :raises IsADirectoryError: If the Pod Spec yaml file path points to a directory
        """
        logger.info(f"Creating pod {pod_spec} in namespace {namespace}")
        with open(str(pod_spec)) as f:
            pod_spec = yaml.safe_load(f)

        pod: V1Pod = self._corev1_api.create_namespaced_pod(namespace=namespace, body=pod_spec)
        logger.info(f"Created pod with name {pod.metadata.name}")
        return pod.metadata.name

    def _get_pod_status(self, pod_name: str):
        """
        Gets pod status
        :param pod_name: The name of the pod
        :return: A PodStatus object with the status of the pod. If the pod is not found,
        no exceptions are raised, but rather PodStatus.NOT_FOUND is returned.
        :raises ApiException: When there is an error calling the Kubernetes API
        """
        logging.info(f"Getting status for pod: {pod_name}")
        try:
            pod = self._corev1_api.read_namespaced_pod_status(namespace=self._namespace, name=pod_name)
        except ApiException as err:
            if err.status == 404:
                logger.debug(f"Pod {pod_name} not found in namespace {self._namespace}")
                return PodStatus.NOT_FOUND
            raise err
        status = PodStatus(pod.status.phase.lower())
        logging.info(f"Status for pod {pod_name}: {status}")
        return status

    def _delete_pod(self, pod_name: str, ignore_not_found: bool = False):
        """
        Deletes a pod
        :param pod_name: The name of the pod to delete
        :param ignore_not_found: Whether or not to raise an ApiException in case the pod is not found
        :raises ApiException: When there is an error calling the Kubernetes API
        """
        logger.info(f"Deleting {pod_name}")
        try:
            self._corev1_api.delete_namespaced_pod(namespace=self._namespace, name=pod_name)
        except ApiException as err:
            if err.status == 404 and ignore_not_found:
                logger.debug(f"Pod {pod_name} not found in namespace {self._namespace}")
                return
            logger.exception(err)
            raise err

    def _clean_up(self, server_pod_name: Optional[str] = None, benchmark_pod_name: Optional[str] = None):
        """
        Deletes server and/or benchmark pods. To be called before the benchmark execution finishes to
        clean up any kubernetes data.
        :param server_pod_name: Server pod name, or None
        :param benchmark_pod_name: Benchmark pod name, or None
        """
        logger.info("Cleaning up pods")
        if server_pod_name:
            self._delete_pod(server_pod_name, ignore_not_found=True)
        if benchmark_pod_name:
            self._delete_pod(benchmark_pod_name, ignore_not_found=True)

    @staticmethod
    def _is_benchmark_finished(benchmark_status: PodStatus, server_status: PodStatus) -> bool:
        """
        Checks on the execution status of the inference benchmark.
        :returns True: if the benchmark has finished successfully
        :returns False: if the benchmark is still executing
        :raises InferenceBenchmarkFailedError: If there is an error executing the benchmark
        """
        logger.info(f"Benchmark: {benchmark_status}; Server: {server_status}")

        # benchmark finished -> kill server pod and return success/failure
        if benchmark_status.is_final() or benchmark_status == PodStatus.NOT_FOUND:
            if benchmark_status.is_successful():
                return True
            else:
                raise InferenceBenchmarkFailedError(f"Benchmark terminated with status: '{benchmark_status}'")

        # server pod finished -> automatic failure, server pods should never finish
        if server_status.is_final() or server_status == PodStatus.NOT_FOUND:
            raise InferenceBenchmarkFailedError(
                f"Benchmark failed. Inference server terminated with status '{server_status}'"
            )

        return False

    def execute(self):
        """
        Executes the inference benchmark by creating and monitoring the benchmark and inference server pods.
        Deletes created pods before exiting.
        :raises InferenceBenchmarkFailedError: If there is an error executing the benchmark
        """
        server_pod_name = None
        benchmark_pod_name = None

        try:
            logging.info(f"Executing benchmark: {self._benchmark_pod_spec} against server: {self._server_pod_spec}.")
            logging.info(f"Starting pods...")
            server_pod_name = self._create_pod(namespace=self._namespace, pod_spec=self._server_pod_spec)
            benchmark_pod_name = self._create_pod(namespace=self._namespace, pod_spec=self._benchmark_pod_spec)

            for _ in itertools.count():
                server_status = self._get_pod_status(pod_name=server_pod_name)
                benchmark_status = self._get_pod_status(pod_name=benchmark_pod_name)

                if self._is_benchmark_finished(benchmark_status, server_status):
                    logging.info("Successfully completed benchmark")
                    break

                logging.info("Benchmark still running...")
                time.sleep(self.SLEEP_TIME)
        except Exception as err:
            raise InferenceBenchmarkFailedError(str(err)) from err
        finally:
            self._clean_up(server_pod_name=server_pod_name, benchmark_pod_name=benchmark_pod_name)
