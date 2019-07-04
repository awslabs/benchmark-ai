from typing import Dict


class ServiceLabels:
    ACTION_ID_LABEL = "action-id"

    CLIENT_ID_LABEL = "client-id"

    CREATED_BY_LABEL = "created-by"

    @staticmethod
    def get_labels(service_name: str, client_id: str, action_id: str) -> Dict[str, str]:
        return {
            ServiceLabels.ACTION_ID_LABEL: action_id,
            ServiceLabels.CLIENT_ID_LABEL: client_id,
            ServiceLabels.CREATED_BY_LABEL: service_name,
        }

    @staticmethod
    def get_label_selector(service_name: str, client_id: str, action_id: str = None):
        selector = f"{ServiceLabels.CREATED_BY_LABEL}={service_name}," + f"{ServiceLabels.CLIENT_ID_LABEL}={client_id}"
        if action_id:
            selector += f",{ServiceLabels.ACTION_ID_LABEL}={action_id}"
        return selector
