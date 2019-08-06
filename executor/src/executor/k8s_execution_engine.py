import logging
import subprocess
from subprocess import CalledProcessError, check_output

from bai_k8s_utils.service_labels import ServiceLabels
from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkJob
from bai_kafka_utils.executors.descriptor import DescriptorError
from bai_kafka_utils.executors.execution_callback import ExecutionEngine, ExecutionEngineException
from bai_kafka_utils.utils import DEFAULT_ENCODING

from executor import SERVICE_NAME
from executor.config import ExecutorConfig
from transpiler.bai_knowledge import create_job_yaml_spec, create_scheduled_job_yaml_spec

logger = logging.getLogger(__name__)


class K8SExecutionEngine(ExecutionEngine):
    EXTRA_K8S_YAML = "k8s_yaml"

    ENGINE_ID = "kubernetes"

    JOB_ID_PREFIX = "b-"

    ALL_K8S_RESOURCE_TYPES = ["jobs", "cronjobs", "mpijobs", "configmaps", "rolebindings"]

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
        scripts = event.payload.scripts
        job_id = K8SExecutionEngine.JOB_ID_PREFIX + event.action_id

        try:
            yaml = create_job_yaml_spec(
                descriptor_contents, self.config, fetched_data_sources, scripts, job_id, event=event
            )
            self._kubernetes_apply(yaml)
        except DescriptorError as e:
            logger.exception(f"Error parsing descriptor file")
            raise ExecutionEngineException from e
        except CalledProcessError as e:
            logger.exception(f"Error executing benchmark")
            raise ExecutionEngineException from e

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
            raise ExecutionEngineException from e
        except CalledProcessError as e:
            logger.exception(f"Error creating scheduled benchmark")
            raise ExecutionEngineException from e

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

    def cancel(self, client_id: str, action_id: str):
        label_selector = self._create_label_selector(client_id, action_id)
        resource_types = ",".join(self.ALL_K8S_RESOURCE_TYPES)

        cmd = [self.config.kubectl, "delete", resource_types, "--selector", label_selector]
        logger.info(f"Deleting resources of types {resource_types} matching selector {label_selector}")

        result = subprocess.check_output(cmd).decode(DEFAULT_ENCODING)

        # kubectl delete exits with 0 even if there are no resources to delete, so we need to handle that case ourselves
        if "No resources found" in result:
            raise ValueError(f"No resources found matching selector {label_selector}")

        logging.info(f"Succesfully cancelled benchmark with id {action_id}")
        logger.info(f"Kubectl output: {result}")
        return result

    @staticmethod
    def _create_label_selector(client_id: str, action_id: str):
        return ServiceLabels.get_label_selector(SERVICE_NAME, client_id, action_id)
