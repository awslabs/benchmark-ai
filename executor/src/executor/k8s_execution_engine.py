import logging
from subprocess import CalledProcessError, check_output

from bai_k8s_utils.service_labels import ServiceLabels
from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkJob
from bai_kafka_utils.executors.descriptor import DescriptorError
from bai_kafka_utils.executors.execution_callback import (
    ExecutionEngine,
    ExecutionEngineException,
    NoResourcesFoundException,
)
from bai_kafka_utils.utils import DEFAULT_ENCODING

from executor import SERVICE_NAME
from executor.config import ExecutorConfig
from transpiler.bai_knowledge import create_job_yaml_spec, create_scheduled_job_yaml_spec

logger = logging.getLogger(__name__)


class NoK8sResourcesFoundError(Exception):
    pass


class K8SExecutionEngine(ExecutionEngine):
    EXTRA_K8S_YAML = "k8s_yaml"

    ENGINE_ID = "kubernetes"

    JOB_ID_PREFIX = "b-"

    ALL_K8S_RESOURCE_TYPES = ["jobs", "cronjobs", "mpijobs", "configmaps", "rolebindings", "services"]

    def __init__(self, config: ExecutorConfig):
        self.config = config

    def run(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        """
        Creates k8s resources for a single run benchmark
        :param event: The fetcher benchmark event initiating the benchmark
        :return: a Benchmark job
        """
        descriptor_contents = event.payload.toml.contents
        fetched_data_sources = event.payload.datasets
        fetched_models = event.payload.models
        scripts = event.payload.scripts
        job_id = K8SExecutionEngine.JOB_ID_PREFIX + event.action_id

        try:
            yaml = create_job_yaml_spec(
                descriptor_contents, self.config, fetched_data_sources, fetched_models, scripts, job_id, event=event
            )
            self._kubernetes_apply(yaml)
        except DescriptorError as e:
            logger.exception(f"Error parsing descriptor file")
            raise ExecutionEngineException(f"Error parsing descriptor file: {str(e)}") from e
        except CalledProcessError as e:
            logger.exception(f"Error executing benchmark")
            raise ExecutionEngineException(f"Error executing benchmark: {str(e)}") from e

        return BenchmarkJob(id=job_id, extras={K8SExecutionEngine.EXTRA_K8S_YAML: yaml})

    def schedule(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        """
        Creates k8s resources for a scheduled benchmark
        :param event: The fetcher benchmark event initiating the benchmark
        :return: a Benchmark job
        """
        descriptor_contents = event.payload.toml.contents
        job_id = K8SExecutionEngine.JOB_ID_PREFIX + event.action_id

        try:
            yaml = create_scheduled_job_yaml_spec(descriptor_contents, self.config, job_id, event=event)
            self._kubernetes_apply(yaml)
        except DescriptorError as e:
            logger.exception(f"Error parsing descriptor file")
            raise ExecutionEngineException(f"Error parsing descriptor file: {str(e)}") from e
        except CalledProcessError as e:
            logger.exception(f"Error creating scheduled benchmark")
            raise ExecutionEngineException(f"Error executing benchmark: {str(e)}") from e

        return BenchmarkJob(id=job_id, extras={K8SExecutionEngine.EXTRA_K8S_YAML: yaml})

    def _kubernetes_apply(self, yaml: str):
        # Shelling out this command because the kubernetes python client does not have a good way to
        # call kubectl apply -f my_config.yaml (https://github.com/kubernetes-client/python/issues/387)
        # Specially https://github.com/kubernetes-client/python/pull/655 - CRDs not supported
        cmd = [self.config.kubectl, "apply", "-f", "-"]

        logger.info(f"Applying yaml file using command: {cmd}")
        result = check_output(cmd, input=yaml.encode(DEFAULT_ENCODING))
        logger.info(f"Kubectl output: {result}")
        logger.info(f"Job submitted with yaml:\n{yaml}")

    def cancel(self, client_id: str, action_id: str, cascade: True):

        results = []
        try:
            results.append(self._cancel(client_id, action_id, as_parent=False))
        except NoK8sResourcesFoundError as err:
            # Only throw no resources found error when not cascading the deletion
            # Use-case: User deletes scheduled benchmark without cascading, and now would
            # like to delete the spawned jobs.
            if not cascade:
                raise NoResourcesFoundException(action_id) from err
        except Exception as err:
            raise ExecutionEngineException(str(err)) from err

        if cascade:
            try:
                results.append(self._cancel(client_id, action_id, as_parent=True))
            except NoK8sResourcesFoundError as err:
                raise NoResourcesFoundException(action_id) from err
            except Exception as err:
                raise ExecutionEngineException(str(err)) from err

        return results

    def _cancel(self, client_id: str, action_id: str, as_parent: bool):
        label_selector = self._create_label_selector(client_id, action_id, as_parent)
        result = self._delete_k8s_resources(label_selector)

        if as_parent:
            logging.info(f"Succesfully cancelled benchmarks with parent-action-id {action_id}")
        else:
            logging.info(f"Succesfully cancelled benchmark with id {action_id}")
        logger.info(f"Kubectl output: {result}")
        return result

    def _delete_k8s_resources(self, label_selector: str):
        if not label_selector:
            raise RuntimeError("Attempting to delete kubernetes resources without label selector")

        resource_types = ",".join(self.ALL_K8S_RESOURCE_TYPES)

        cmd = [self.config.kubectl, "delete", resource_types, "--selector", label_selector]
        logger.info(f"Deleting resources of types {resource_types} matching selector {label_selector}")

        result = check_output(cmd).decode(DEFAULT_ENCODING)
        if "No resources found" in result:
            raise NoK8sResourcesFoundError(f"No resources found matching selector {label_selector}")

        return result

    @staticmethod
    def _create_label_selector(client_id: str, action_id: str, as_parent: bool):
        if as_parent:
            return ServiceLabels.get_label_selector_as_parent(SERVICE_NAME, client_id, action_id)
        return ServiceLabels.get_label_selector(SERVICE_NAME, client_id, action_id)
