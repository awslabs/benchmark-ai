import os
import csv

GPU_PREFIXES = ["g", "p"]


def get_instance_gpus(instance_type: str) -> int:
    file_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(file_dir, os.pardir, "util", "ec2_instance_info.csv"), mode="r") as infile:
        reader = csv.reader(infile)
        gpus_per_instance = {rows[0]: rows[1] for rows in reader}

    if instance_type in gpus_per_instance:
        return gpus_per_instance[instance_type]

    # Instance type not in mapping. Is it a GPU instance? If not, just assume it's a CPU instance
    if instance_type[0] not in GPU_PREFIXES:
        return 0

    raise Exception(
        f"Determining the number of installed GPUs for the instance type {instance_type} is not yet supported"
    )
