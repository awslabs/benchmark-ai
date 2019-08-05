import logging
import os
import time
import signal
from kubernetes import client, config
from kubernetes.client import V1Pod, V1ContainerState, V1ContainerStateTerminated
from threading import Thread


logger = logging.getLogger(__name__)


def start_kubernetes_pod_watcher(pod_name: str, pod_namespace: str):
    # HACK: While Kubernetes doesn't provide first class support for sidecar containers in Jobs,
    # (see: https://github.com/kubernetes/kubernetes/issues/25908), then we simulate it with
    # our own thread that watches the benchmark container. It is not perfect, but it's good enough
    thread = Thread(
        target=watch_kubernetes_pod, name="watch-kubernetes-pod", args=(pod_name, pod_namespace), daemon=True
    )
    thread.start()
    return thread


def watch_kubernetes_pod(pod_name: str, namespace: str):
    logger.info("Watch pod thread entered")
    config.load_incluster_config()
    logger.info("Config loaded")
    v1 = client.CoreV1Api()
    logger.info("v1 here")

    while True:
        logger.info("Before get pod status")
        try:
            v1pod: V1Pod = v1.read_namespaced_pod_status(pod_name, namespace)
        except Exception as e:
            logger.info("Caught something %s", str(e))
            raise
        finally:
            logger.info("After get pod")
        logger.info("pod %s read = %s", pod_name, str(v1pod))

        container_status_mapping = {
            container_status.name: container_status for container_status in v1pod.status.container_statuses
        }
        state: V1ContainerState = container_status_mapping["benchmark"].state
        terminated: V1ContainerStateTerminated = state.terminated
        logger.info("Container state: %s", state)

        if terminated:
            os.kill(os.getpid(), signal.SIGTERM)
            break
        else:
            # Sleep because we don't want to overload the API server
            time.sleep(1)
