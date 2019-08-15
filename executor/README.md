# Descriptor file

A descriptor file defines a benchmark job. This directory contains a template descriptor including explanatory comments
 on all fields. The descriptor is written in [TOML 0.4.0](https://github.com/toml-lang/toml/blob/master/versions/en/toml-v0.4.0.md).

The file is divided in sections: info, hardware, env, ml, data and output. See the example descriptor below for reference.

## Example descriptor

The following example shows what the descriptor file for a horovod-based benchmark looks like.

```toml
# BenchmarkAI meta
spec_version = "0.1.0"

# 0. Job details
[info]
task_name = "Example benchmark"
description = """ \
    Full job description.\
    """
scheduling = 'single_run'

# 1. Hardware
[hardware]
instance_type = "p3.8xlarge"
strategy = "horovod"

# [Opt] Section for distributed (multi node) mode
[hardware.distributed]
# [Upcoming] Strategy to follow
num_instances = 3

# 2. Environment
[env]
# Docker hub <hub-user>/<repo-name>:<tag> 
docker_image = "user/repo:tag"
# Args for the docker container
# [Opt] Whether to run the container in privileged mode (default is false)
privileged = false
# [Opt] Whether more than 64MB shared memory is needed for containers (default is true)
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
path = "/data/tf-imagenet/train"

# Second data source
[[data.sources]]
# Data download URI.
uri = "s3://bucket/imagenet/validation"
# Path where the dataset is stored in the container FS
path = "/data/tf-imagenet/val"
```


## Fields

| Section                | Field          | Description                                                                                                                                            | Values                                                      | Required/Optional |
|------------------------|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|-------------------|
| -                      | spec_version   | Version of the descriptor specification                                                                                                                | Semantically versioned                                      | Required          |
| info                   | task_name      | Name of the benchmark job                                                                                                                              | String                                                      | Required          |
| info                   | description    | Description (informative field)                                                                                                                        | String                                                      | Required          |
| info                   | scheduling     | Job scheduling: whether to run it a single time or periodically and when    | [Cron expression](https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/#schedule) to schedule a job, 'single_run' to run it right away (default)| Optional |
| hardware               | instance_type  | Type of EC2 instance where the job is to run                                                                                                           | EC2 instance [API name](https://ec2instances.info)          | Required          |
| hardware               | strategy       | Whether to run on single node or distributed. In the latter case, a distributed strategy, such as horovod or mxnet_parameter_server, must be specified | One of ['single_node', 'horovod', 'mxnet_parameter_server'] | Required          |
| hardware > distributed | num_instances  | Number of nodes to use for distributed training                                                                                                        | Int                                                         | Optional          |
| env                    | docker_image   | Docker image which runs the benchmark (it must contain the benchmark code)                                                                             | Docker image as user/repo:tag                               | Required          |
| env                    | privileged     | Whether to run the container in privileged mode                                                                                                        | boolean (default: false)                                    | Optional          |
| env                    | extended_shm   | Whether more than 64MB shared memory is needed for containers                                                                                          | boolean (default: true)                                     | Optional          |
| ml                     | benchmark_code | Command to run the benchmark code                                                                                                                      | String                                                      | Optional          |
| ml                     | args           | Additional arguments for the benchmark scripts                                                                                                         | String                                                      | Optional          |
| data                   | id             | Dataset name                                                                                                                                           | String ('imagenet', 'cifar10', etc.)                        | Required          |
| data                   | sources        | List with all required data sources (see below for the fields required for each source)                                                                | List of data.sources                                        | Optional          |
| data > sources         | uri            | Uri of the dataset to be downloaded. We plan to support 's3', 'http', 'https', 'ftp' and 'ftps'                                                        | Uri, such as 's3://bucket/imagenet/'                        | Optional          |
| data > sources         | path           | Destination path where this data will be mounted in the container FS                                                                                   | String                                                      | Optional          |

Notes on the sections:

* **Info**: The scheduling field lets users specify when the job is supposed to run. This is done using cron expressions, such as `0 * * * *` or `@daily`, for example.
* **Hardware**: Users must specify a strategy to run their benchmark, be it single_node or one of the distributed alternatives, such as horovod.
* **Env**: Environment is defined by passing the identifier (user/repo:tag) of the docker image containing the benchmark code.
* **Ml**: Users can specify the command to run on their docker image (benchmark_code) or the args to be passed to the container's entrypoint. If both are specified, the args are concatenated with the command.
* **Data**: This section must specify the ID of the dataset used, along with a list of the data sources to be downloaded.
For any required data source, users can provide a download URI and a destination path where the resulting data will be mounted in the container filesystem for the benchmark script to use it.
* (Upcoming) **Output**: Section for users to declare the metrics they will be tracking with this benchmark, along with the alarming information: thresholds (can be dynamic, such as 2-sigma) and who should be notified when they are triggered.


## Descriptor reader

The descriptor_reader Python script is provided to parse descriptor files and generate the corresponding Kubernetes job configuration YAML file. It is called as follows:

```
python descriptor_reader.py path_to_descriptor.toml
```

This utility is used by the baictl CLI to run Kubernetes jobs.

## Integration tests

To help in development and testing of the service, use [kind](https://github.com/kubernetes-sigs/kind) to locally simulate a kubernetes cluster.
Once installed, bring up the cluster with `kind create cluster --image=$K8S_KINDEST_V12 --config=integration-test-cluster.yml`. When finished,
update your kubeconfig environment variable with `export KUBECONFIG="$(kind get kubeconfig-path --name="kind")"`. Then, follow the steps in the
*build* section of the [buildspec.yaml](buildspec.yml).

NOTE: keep in mind that the docker images will need to be pulled by the docker nodes. This could affect test outcomes, so keep it this in mind.
