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
from dataclasses import dataclass, field
from typing import List

from bai_kafka_utils.executors.descriptor import DescriptorConfig

from transpiler.config import BaiConfig, EnvironmentInfo


@dataclass
class ExecutorConfig:
    # TODO: Create a transpilerConfig with the fields below, we shouldnt be passing
    # information such as kubectl to the transpiler
    descriptor_config: DescriptorConfig
    bai_config: BaiConfig
    environment_info: EnvironmentInfo
    kubectl: str
    valid_execution_engines: List[str] = field(default_factory=list)
