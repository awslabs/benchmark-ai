import subprocess
import logging

from executor import SERVICE_NAME
from bai_kafka_utils.utils import DEFAULT_ENCODING


logger = logging.getLogger(SERVICE_NAME)


class ExecutorCommandObject:
    LABEL_ACTION_ID = "action-id"
    LABEL_CREATED_BY = "created-by"
    LABEL_CLIENT_ID = "client-id"

    # This lists all the resource types we have in our cluster.
    # When deleting, we use the label selector to choose what gets removed.
    ALL_K8S_RESOURCE_TYPES = ["jobs", "cronjobs", "mpijobs", "configmaps"]

    def __init__(self, kubectl: str):
        self.kubectl = kubectl

    def cancel(self, target_action_id: str, client_id: str):
        label_selector = self._create_label_selector(target_action_id, client_id)
        resource_types = ",".join(self.ALL_K8S_RESOURCE_TYPES)

        cmd = [self.kubectl, "delete", resource_types, "--selector", label_selector]
        logger.info(f"Deleting resources of types {resource_types} matching selector {label_selector}")

        result = subprocess.check_output(cmd).decode(DEFAULT_ENCODING)

        # kubectl delete exits with 0 even if there are no resources to delete, so we need to handle that case ourselves
        if "No resources found" in result:
            raise ValueError(f"No resources found matching selector {label_selector}")

        logging.info(f"Succesfully cancelled benchmark with id {target_action_id}")
        logger.info(f"Kubectl output: {result}")
        return result

    def _create_label_selector(self, action_id: str, client_id: str):
        return (
            f"{self.LABEL_ACTION_ID}={action_id},"
            f"{self.LABEL_CREATED_BY}={SERVICE_NAME},"
            f"{self.LABEL_CLIENT_ID}={client_id}"
        )
