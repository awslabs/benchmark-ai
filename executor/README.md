# Descriptor file

A descriptor file defines a benchmark job. This directory contains a template descriptor including explanatory comments
 on all fields. The descriptor is written in [TOML 0.4.0](https://github.com/toml-lang/toml/blob/master/versions/en/toml-v0.4.0.md) (and validated via [this schema](bai-bff/resources/descriptor_schema.json))

The file is divided in sections: info, hardware, env, ml, data and output. See the example descriptor below for reference.

## Example descriptors


### Training

The following example shows what the descriptor file for a horovod-based training benchmark looks like.

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

[info.labels]
# Labels and values must be 63 characters or less, beginning and ending with an alphanumeric character
# ([a-z0-9A-Z]) with dashes (-), underscores (_), dots (.), and alphanumerics between
custom-label = "value"
other-label = "other-value"

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

# [Opt] Data sources
# List all required data sources below.
# Make an entry for each with the same format as the ones below.
[[data.sources]]
# Data download URI.
uri = "s3://bucket/imagenet/train"
# Path where the dataset is stored in the container FS
path = "/data/tf-imagenet/train"
# Md5 can be ommitted, but it is required for dataset caching to work
md5 = "5df9f63916ebf8528697b629022993e8"

# Second data source
[[data.sources]]
# Data download URI.
uri = "s3://bucket/imagenet/validation"
# Path where the dataset is stored in the container FS
path = "/data/tf-imagenet/val"

# 5. Output
[output]
# [Opt] Custom metrics descriptions
# List all required metrics descriptions below.
# Make an entry in same format as the one below.
[[output.metrics]]
# Name of the metric that will appear in the dashboards.
name = "accuracy"

# Metric unit (required)
units = "ratio"

# Pattern for log parsing for this metric.
pattern = "accuracy=([-+]?\\d*\\.\\d+|\\d+)"

```

### Inference

Inference benchmarks use a client-server architecture, where the client sends requests to the host, which contains the ML model.
To describe such a job, specify `strategy = "inference"` and add a section describing the server:

```toml
# BenchmarkAI meta
spec_version = "0.1.0"

# These fields don't have any impact on the job to run, they contain
# merely informative data so the benchmark can be categorized when displayed
# in the dashboard.
[info]
task_name = "Example inference job"
description = "A sample scheduled inference benchmark"
scheduling = "*/1 * * * *"

[info.labels]
# Labels and values must be 63 characters or less, beginning and ending with an alphanumeric character
# ([a-z0-9A-Z]) with dashes (-), underscores (_), dots (.), and alphanumerics between
custom-label = "value"
other-label = "other-value"

# Benchmark definition
# 1. Hardware
[hardware]
instance_type = "t3.medium"
strategy = "inference"

# 2. Environment
[env]
# Docker hub <hub-user>/<repo-name>:<tag>
docker_image = "user/repo:tag"
# Args for the docker container
# [Opt] Whether to run the container in privileged mode (default is false)
privileged = false
# [Opt - default is false] Whether more than 64MB shared memory is needed for containers
# (See docker's -shm option)
extended_shm = true

# 3. Machine learning related settings:
# dataset, benchmark code and parameters it takes
[ml]
benchmark_code = "python /home/benchmark/benchmark_server.py"
# [Opt] Arguments to pass to the script in ml.benchmark_code
# The code is called as defined in ml.benchmark_code, plus the args defined here
# INFERENCE_SERVER_HOST and INFERENCE_SERVER_PORT(_X), where X >= 1, environment variables are
# injected into the benchmark container
args = "--host=${INFERENCE_SERVER_HOST} --port=${INFERENCE_SERVER_PORT} --request-timeout=5 "

# [Opt] 4. Dataset
[data]

# [Opt] Data sources
# List all required data sources below.
# Make an entry for each with the same format as the ones below.
[[data.sources]]
# Data download URI.
src = "s3://example/imagenet/train"
# Path where the dataset is stored in the container FS
path = "/data/imagenet/train"
md5 = "5df9f63916ebf8528697b629022993e8"

# Second data source
[[data.sources]]
# Data download URI.
src = "s3://example/imagenet/validation"
# Path where the dataset is stored in the container FS
path = "/data/imagenet/validation"

# 6. Server definition
[server]
# Harware on which to run the server
[server.hardware]
instance_type = "p3.8xlarge"

[[server.models]]
src = "uri://path/to/model1"
path = "/models/model1"

# The server environment definition
[server.env]
# The server image
docker_image = "user/repo:tag"
# Args for the docker container
# [Opt] Whether to run the container in privileged mode (default is false)
privileged = false
# [Opt - default is false] Whether more than 64MB shared memory is needed for containers
# (See docker's -shm option)
extended_shm = true
# array ports that are exposed by the server
ports = [8080, 8081]
# [Opt] Server iveliness probe url
liveliness_probe = "http://localhost:8080/iamhere"
# [Opt] Server readiness probe url
readiness_probe = "http://localhost:8081/iamok"
# Server start command
start_command = "/opt/bin/server"
# [Opt] Arguments to pass to server start command
start_command_args = "--model=mnist"
# [Opt] Server environment variables

[server.env.vars]
VAR1 = "value1"
VAR2 = "value2"

```

## Fields

| Section                | Field            | Description                                                                                                                                            | Values                                                      | Required/Optional |
|------------------------|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|-------------------|
| -                      | spec_version       | Version of the descriptor specification                                                                                                              | Semantically versioned                                      | Required          |
| info                   | task_name          | Name of the benchmark job                                                                                                                            | String                                                      | Required          |
| info                   | description        | Description (informative field)                                                                                                                      | String                                                      | Required          |
| info                   | scheduling         | Job scheduling: whether to run it a single time or periodically and when    | [Cron expression](https://kubernetes.io/docs/tasks/job/automated-tasks-with-cron-jobs/#schedule) to schedule a job, 'single_run' to run it right away (default)| Optional |
| hardware               | instance_type      | Type of EC2 instance where the job is to run                                                                                                         | EC2 instance [API name](https://ec2instances.info)          | Required          |
| hardware               | strategy           | Whether to run on single node or distributed. In the latter case, a distributed strategy, such as horovod or mxnet_parameter_server, must be specified | One of ['single_node', 'horovod', 'client_server', 'mxnet_parameter_server'] | Required          |
| hardware.distributed   | num_instances      | Number of nodes to use for distributed training                                                                                                      | Int                                                         | Optional          |
| env                    | docker_image       | Docker image which runs the benchmark (it must contain the benchmark code)                                                                           | Docker image as user/repo:tag                               | Required          |
| env                    | privileged         | Whether to run the container in privileged mode                                                                                                      | boolean (default: false)                                    | Optional          |
| env                    | extended_shm       | Whether more than 64MB shared memory is needed for containers                                                                                        | boolean (default: true)                                     | Optional          |
| ml                     | benchmark_code     | Command to run the benchmark code                                                                                                                    | String                                                      | Optional          |
| ml                     | args               | Additional arguments for the benchmark scripts                                                                                                       | String                                                      | Optional          |
| data                   | sources            | List with all required data sources (see below for the fields required for each source)                                                              | List of data.sources                                        | Optional          |
| data.sources           | uri                | Uri of the dataset to be downloaded. We plan to support 's3', 'http', 'https', 'ftp' and 'ftps'                                                      | Uri, such as 's3://bucket/imagenet/'                        | Optional          |
| data.sources           | path               | Destination path where this data will be mounted in the container FS                                                                                 | String                                                      | Optional          |                                                                                                                    |
| data.sources           | md5                | md5 checksum of the file specified above. It is required for the system to be able to cache datasets                                                 | String                                                      | Optional          |                                                                                                                    |
| server                     |                        | Defines an inference server - only relevant for the *inference* strategy.                                                                              |                                                             | Required for *client-server* strategy
| server                     | hardware               | Hardware definition for inference server                                                                                                               |                                                             | Required           |
| server.hardware            | instance_type          | Inference server EC2 instance type                                                                                                                     | String                                                      | Required           |
| server                     | env                    | Inference server environment definition                                                                                                                |                                                             | Required           |
| server.env                 | docker_image           | Inference server docker image                                                                                                                          | String                                                      | Required           |
| server.env                 | privileged             | Whether to run the container in privileged mode                                                                                                        | Boolean (default: false)                                    | Optional           |
| server.env                 | extended_shm           | Whether more than 64MB shared memory is needed for containers                                                                                          | Boolean (default: true)                                     | Optional           |
| server.env                 | ports                  | The inference server ports                                                                                                                             | List of integers                                            | Required           |
| server.env                 | start_command          | Command to be executed to start the server                                                                                                             | String                                                      | Required           |
| server.env                 | start_command_args     | Arguments to pass to server start command                                                                                                              | String                                                      | Optional           |
| server.env                 | vars                   | Server environment variables section                                                                                                                   | Key-value pairs                                             | Optional           |
| server.env.readiness_probe |                        | Server readiness probe                                                                                                                                 |                                                             | Optional           |
| server.env.readiness_probe | path                   | Server path to probe                                                                                                                                   | Readiness endpoint path                                     | Required           |
| server.env.readiness_probe | scheme                 | URI Scheme                                                                                                                                             | http or https (default: http)                               | Optional           |
| server.env.readiness_probe | port                   | Server probe port                                                                                                                                      | Integer between 1 and 65535 (Defaults to first server port) | Optional           |
| server.env.readiness_probe | initial_delay_seconds  | Number of seconds after server container starts to initiate probe                                                                                      | Integer >= 1 (default: 10)                                  | Optional           |
| server.env.readiness_probe | period_seconds         | How often to perform probe                                                                                                                             | Integer >= 1 (default: 10)                                  | Optional           |
| server.env.readiness_probe | timout_seconds         | Number of seconds after which probe will timeout                                                                                                       | Integer >= 1 (default: 1)                                   | Optional           |
| server.env.readiness_probe | success_threshold      | Minimum consecutive successes for probe to be considered successful                                                                                    | Integer >= 1 (default: 1)                                   | Optional           |
| server.env.readiness_probe | failure_threshold      | Minimum consecutire failured for probe to be considered failed                                                                                         | Integer >= 1 (default: 3)                                   | Optional           |

Notes on the sections:

* **Info**: The scheduling field lets users specify when the job is supposed to run. This is done using cron expressions, such as `0 * * * *` or `@daily`, for example.
* **Hardware**: Users must specify a strategy to run their benchmark, be it single_node or one of the distributed alternatives, such as horovod.
* **Env**: Environment is defined by passing the identifier (user/repo:tag) of the docker image containing the benchmark code.
* **Ml**: Users can specify the command to run on their docker image (benchmark_code) or the args to be passed to the container's entrypoint. If both are specified, the args are concatenated with the command.
* **Data**: This section must specify a list of the data sources to be downloaded.
For any required data source, users can provide a download URI and a destination path where the resulting data will be mounted in the container filesystem for the benchmark script to use it.
* **Server**: This section must specify the inference server hardware and environment. It is only relevant to the *inference* strategy.
* (Upcoming) **Output**: Section for users to declare the metrics they will be tracking with this benchmark, along with the alarming information: thresholds (can be dynamic, such as 2-sigma) and who should be notified when they are triggered.


## Integration tests

To help in development and testing of the service, use [kind](https://github.com/kubernetes-sigs/kind) to locally simulate a kubernetes cluster.
Once installed, bring up the cluster with `kind create cluster --image=$K8S_KINDEST_V12 --config=integration-test-cluster.yml`. When finished,
update your kubeconfig environment variable with `export KUBECONFIG="$(kind get kubeconfig-path --name="kind")"`. Then, follow the steps in the
*build* section of the [buildspec.yaml](buildspec.yml).

NOTE: keep in mind that the docker images will need to be pulled by the docker nodes. This could affect test outcomes, so keep it this in mind.
