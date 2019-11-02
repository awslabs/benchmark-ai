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
import os
import csv
import logging

GPU_PREFIXES = ["g", "p"]


def get_instance_gpus(instance_type: str) -> int:
    """
    Determine the number of GPUs that are installed into an EC2 instance type
    :param instance_type: EC2 instance type, e.g. "p3.8xlarge"
    :return: Number of GPUs, e.g. 4
    """
    file_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(file_dir, os.pardir, "util", "ec2_instance_info.csv"), mode="r") as infile:
        reader = csv.reader(infile)
        gpus_per_instance = {rows[0]: rows[1] for rows in reader}

    if instance_type in gpus_per_instance:
        return int(gpus_per_instance[instance_type])

    logging.warning(f"Unknown instance type {instance_type} - making assumptions based on prefix...")

    # Instance type not in mapping. Is it a GPU instance? If not, just assume it's a CPU instance
    if instance_type[0] not in GPU_PREFIXES:
        return 0

    raise Exception(
        f"Determining the number of installed GPUs for the instance type {instance_type} is not yet supported"
    )
