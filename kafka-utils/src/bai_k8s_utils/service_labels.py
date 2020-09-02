#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Dict


class ServiceLabels:
    ACTION_ID_LABEL = "action-id"

    PARENT_ACTION_ID_LABEL = "parent-action-id"

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
    def get_labels_as_parent(service_name: str, client_id: str, action_id: str) -> Dict[str, str]:
        return {
            ServiceLabels.PARENT_ACTION_ID_LABEL: action_id,
            ServiceLabels.CLIENT_ID_LABEL: client_id,
            ServiceLabels.CREATED_BY_LABEL: service_name,
        }

    @staticmethod
    def get_label_selector(service_name: str, client_id: str, action_id: str = None):
        additional_labels = {}
        if action_id:
            additional_labels[ServiceLabels.ACTION_ID_LABEL] = action_id

        return ServiceLabels.build_label_selector(service_name, client_id, additional_labels)

    @staticmethod
    def get_label_selector_as_parent(service_name: str, client_id: str, action_id: str):
        additional_labels = {ServiceLabels.PARENT_ACTION_ID_LABEL: action_id}
        return ServiceLabels.build_label_selector(service_name, client_id, additional_labels)

    @staticmethod
    def build_label_selector(service_name: str, client_id: str, additional_labels: Dict[str, str] = None):
        def label(key: str, value: str):
            return f"{key}={value}"

        selectors = [
            label(ServiceLabels.CREATED_BY_LABEL, service_name),
            label(ServiceLabels.CLIENT_ID_LABEL, client_id),
        ]

        if additional_labels:
            for k, v in additional_labels.items():
                selectors.append(label(k, v))

        return ",".join(selectors)
