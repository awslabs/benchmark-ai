# Descriptor file

A descriptor file defines a benchmark job. This directory contains a template descriptor including explanatory comments on all fields. The descriptor is written in [TOML](https://github.com/toml-lang/toml).

The file is divided in sections: info, hardware, env, ml, data and output. See the example descriptor below for reference.

## Example descriptor


```toml
# BenchmarkAI meta
spec_version = "0.1.0"

# These fields don't have any impact on the job to run, they contain
# merely informative data so the benchmark can be categorized when displayed
# in the dashboard.
[info]
task_name = "Example benchmark"
description = """ \
    Full job description.\
    """

# 1. Hardware
[hardware]
instance_type = "p3.8xlarge"

# [Opt] Section for distributed (multi node) mode
[hardware.distributed]
# [Upcoming] Strategy to follow
strategy = "horovod"
num_instances = 3
gpus_per_instance = 8

# 2. Environment
[env]
# Docker hub <hub-user>/<repo-name>:<tag> 
docker_image = "user/repo:tag"
# Args for the docker container
# [Opt] Whether to run the container in privileged mode (default is false)
privileged = false
# [Opt - default is true] Whether more than 64MB shared memory is needed for containers
# (See docker's -shm option)
extended_shm = true

# 3. Machine learning related settings: 
# dataset, benchmark code and parameters it takes
[ml]
# [Opt] Command to run when launching the container (entrypoint is used if not specfied)
benchmark_code = "python /root/train.sh"
# [Opt] Arguments to pass to the script in ml.benchmark_code
# The code is called as defined in ml.benchmark_code, plus the args defined here
args = "--model=resnet50_v2 --batch-size=32"

# [Opt] 4. Dataset 
[data]
# Dataset ID
id = "imagenet"

# [Opt] Data sources
# List all required data sources below. 
# Make an entry for each with the same format as the ones below.
[[data.sources]]
# Data download URI.
uri = "s3://bucket/imagenet/train"
# Path where the dataset is stored in the container FS
path = "~/data/tf-imagenet/"

# Second data source
[[data.sources]]
# Data download URI.
uri = "s3://bucket/imagenet/validation"
# Path where the dataset is stored in the container FS
path = "~/data/tf-imagenet/"

# 4. Output
[output]
# Define which metrics will be tracked in this benchmark
metrics = ["throughput", "time"]
```

#### info
The fields in this section don't have any impact on the job to run, they contain merely informative data about the benchmark job.

#### hardware
Users can choose which kind of EC2 instance they want their code to run on. 

#### env
Environment is defined by passing the Docker Hub user/repo:tag of the docker image containing the benchmark code.

#### ml
This section is for machine-learning related settings: code to run, dataset to use and parameters to pass in.

#### data
This section must specify the ID of the dataset used, along with a list of the data sources to be downloaded.

For any required data source, users can provide a download URI and a destination path where the resulting data should be located in the container filesystem for the benchmark script to use it.

#### output
Section for users to declare the metrics they will be tracking with this benchmark.


## Descriptor reader

The descriptor_reader Python script is provided to parse descriptor files and generate the corresponding Kubernetes job configuration YAML file. It is called as follows:

```
python descriptor_reader.py path_to_descriptor.toml
```

This utility is used by the baictl CLI to run Kubernetes jobs.
