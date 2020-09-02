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
from enum import Enum


class BenchmarkJobStatus(Enum):
    """
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
    """

    # General statuses
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

    # Kubernetes statuses
    NO_POD_SCHEDULED = "NO_POD_SCHEDULED"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"

    FAILED_AT_BENCHMARK_CONTAINER = "FAILED_AT_BENCHMARK_CONTAINER"
    FAILED_AT_SIDECAR_CONTAINER = "FAILED_AT_SIDECAR_CONTAINER"  # Should never occur, but you never know!
    FAILED_AT_INIT_CONTAINERS = "FAILED_AT_INIT_CONTAINERS"

    PENDING_AT_BENCHMARK_CONTAINER = "PENDING_AT_BENCHMARK_CONTAINER"
    PENDING_AT_SIDECAR_CONTAINER = "PENDING_AT_SIDECAR_CONTAINER"
    PENDING_AT_INIT_CONTAINERS = "PENDING_AT_INIT_CONTAINERS"
    PENDING_NODE_SCALING = "PENDING_NODE_SCALING"

    RUNNING_AT_INIT_CONTAINERS = "RUNNING_AT_INIT_CONTAINERS"
    RUNNING_AT_MAIN_CONTAINERS = "RUNNING_AT_MAIN_CONTAINERS"

    # SageMaker statuses
    SM_STOPPED = "STOPPED"
    SM_INTERRUPTED = "SM_INTERRUPTED"
    SM_FAILED_MAX_RUNTIME_EXCEEDED = "SM_FAILED_MAX_RUNTIME_EXCEEDED"
    SM_FAILED_MAX_WAITTIME_EXCEEDED = "SM_FAILED_MAX_WAITTIME_EXCEEDED"

    SM_IN_PROGRESS_STARTING = "SM_IN_PROGRESS_STARTING"
    SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES = "SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES"
    SM_IN_PROGRESS_PREP_TRAINING_STACK = "SM_IN_PROGRESS_PREP_TRAINING_STACK"
    SM_IN_PROGRESS_DOWNLOADING = "SM_IN_PROGRESS_DOWNLOADING"
    SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG = "SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG"
    SM_IN_PROGRESS_TRAINING = "SM_IN_PROGRESS_TRAINING"
    SM_IN_PROGRESS_UPLOADING = "SM_IN_PROGRESS_UPLOADING"
    SM_UNKNOWN = "SM_UNKNOWN"
    SM_STOPPING = "SM_STOPPING"

    def is_final(self):
        """
        Does this state represent a "final state"
        """
        return self in (
            BenchmarkJobStatus.SUCCEEDED,
            BenchmarkJobStatus.FAILED_AT_INIT_CONTAINERS,
            BenchmarkJobStatus.FAILED_AT_BENCHMARK_CONTAINER,
            BenchmarkJobStatus.FAILED_AT_SIDECAR_CONTAINER,
            BenchmarkJobStatus.JOB_NOT_FOUND,
            BenchmarkJobStatus.FAILED,
            BenchmarkJobStatus.SM_STOPPED,
            BenchmarkJobStatus.SM_FAILED_MAX_RUNTIME_EXCEEDED,
            BenchmarkJobStatus.SM_FAILED_MAX_WAITTIME_EXCEEDED,
            BenchmarkJobStatus.SM_INTERRUPTED,
            BenchmarkJobStatus.SM_UNKNOWN,
        )

    def is_running(self):
        return self in (
            BenchmarkJobStatus.RUNNING_AT_INIT_CONTAINERS,
            BenchmarkJobStatus.RUNNING_AT_MAIN_CONTAINERS,
            BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING,
            BenchmarkJobStatus.SM_IN_PROGRESS_STARTING,
            BenchmarkJobStatus.SM_IN_PROGRESS_LAUNCHING_ML_INSTANCES,
            BenchmarkJobStatus.SM_IN_PROGRESS_PREP_TRAINING_STACK,
            BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING,
            BenchmarkJobStatus.SM_IN_PROGRESS_DOWNLOADING_TRAINING_IMG,
            BenchmarkJobStatus.SM_IN_PROGRESS_TRAINING,
            BenchmarkJobStatus.SM_IN_PROGRESS_UPLOADING,
            BenchmarkJobStatus.SM_STOPPING,
        )
