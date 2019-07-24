import logging

from bai_kafka_utils.events import FetcherBenchmarkEvent, BenchmarkJob
from bai_kafka_utils.executors.descriptor import DescriptorError
from bai_kafka_utils.executors.execution_callback import ExecutionEngine, ExecutionEngineException

from bai_kafka_utils.utils import DEFAULT_ENCODING
from subprocess import CalledProcessError, check_output

from executor.config import ExecutorConfig
from transpiler.bai_knowledge import create_job_yaml_spec


logger = logging.getLogger(__name__)


class K8SExecutionEngine(ExecutionEngine):
    EXTRA_K8S_YAML = "k8s_yaml"

    ENGINE_ID = "kubernetes"

    JOB_ID_PREFIX = "b-"

    def __init__(self, config: ExecutorConfig):
        self.config = config

    def cancel(self, client_id: str, action_id: str):
        pass

    def run(self, event: FetcherBenchmarkEvent) -> BenchmarkJob:
        descriptor_contents = event.payload.toml.contents
        fetched_data_sources = event.payload.datasets
        job_id = K8SExecutionEngine.JOB_ID_PREFIX + event.action_id

        try:
            yaml = create_job_yaml_spec(descriptor_contents, self.config, fetched_data_sources, job_id, event=event)
            self._kubernetes_apply(yaml)
        except DescriptorError as e:
            logger.exception(f"Error parsing descriptor file")
            raise ExecutionEngineException from e
        except CalledProcessError as e:
            logger.exception(f"Error executing benchmark")
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
