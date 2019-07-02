A "framework" that enables to periodically generate performance benchmarks of Machine Learning systems in order to evaluate new functionalities and detect regressions.

# A "framework" ?

Benchmark AI provides a simple, self service solution for teams to schedule and run benchmarks for Machine Learning systems.
It allows teams to spin-up the required infrastructure and automation needed to perform benchmarks. Using BenchmarkAI,
users can monitor the evolution of their benchmarks over time to detect anomalies or regressions. Alarms can be
configured to notify the corresponding teams when certain metrics exceed given thresholds. 

# Usage

Benchmark AI provides the `baictl` (BAI = Benchmark AI, ctl = control...clever huh!) utility.
It is useful to:

- create the infrastructure: `baictl create infra`
- run a benchmark: `baictl run benchmark --descriptor=resnet50-descriptor.toml`
- obtain information from a benchmark that was run: `baictl get benchmark --name=benchmark-id`

For more information on all commands, please see the [full documentation]() of `baictl`.

# Build status

| Project        | badge                                                                                                                                                                                                                                                                                                                     |
| :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| baictl         | ![baictl](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiVS8vVlRqQ1RPT1EwTnNqZ0xtT20wZGNnaGNMUTI0Q25Sd0ltcFI5ZklaVm5IbWhQMnFtZHNLaGVpQXdwYmdrTld6cGlQMU9RSERTL01lSytiUmI3Nk9RPSIsIml2UGFyYW1ldGVyU3BlYyI6Im03RHZBdzBmZ1FHaEJDZTAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)         |
| bff            | ![bff](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiSmRSWlVRZ1FxRHJLQWdrTkI2NUpmeXljMTVob2pUV0YyaHh6b0duQVdHaE5RZStxc2pXTnJlQkE5eDdxM1JDYUx0UXFLdWJ5bzZudGg0c0VtTmRhR0VJPSIsIml2UGFyYW1ldGVyU3BlYyI6IkFEMlVmb3JBK2lxUkp6dUEiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)            |
| client-lib     | ![client-lib](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiRG5sWDZmeEdScVJuaDZLMzZuUC8xU2taSFZVeTd4dkFjMk43THJTc1J6QldaSUpKQkNDSGxCSVV2VEJ1OHVsQ1IrcFgrV2lSN01rUWFYKysxS3NqN1BJPSIsIml2UGFyYW1ldGVyU3BlYyI6InZUOUNpWmVIWjNxVmloVTEiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)     |
| executor       | ![executor](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiM0FMS0x1MUhaRjRGU3l1S1IxUUF6UDBLaWw1dkpwcFhXSytLbWM1QlJOR21ZNnFOVVNzM2xRMTFLajRmbExjbDRrWGxRK1Q0eFlrMTVGczE4NXdSK00wPSIsIml2UGFyYW1ldGVyU3BlYyI6IjFVK0trKzNoMnJjS1FJSjQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)       |
| fetcher        | ![fetcher](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiczR0eGlwcnBPMEd2VEtBUzcrMy9VaWRmT3FjZ0xWeU9lZ25tUTY2c2lnYzNacWVVOE5uaWhXcEUzUzNLalQwcnBXSy9LQ2poa3AzTGpFalhIejhVUjNjPSIsIml2UGFyYW1ldGVyU3BlYyI6IkZSZi9KWURjaHVqcldCOVMiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)        |
| fetcher-job    | ![fetcher-job](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiSmRYdVZWSE1Yd05KVzBDM1lEL1MzVUJwaVprUmwxMmdLQVQwVWY4czFRb2JUK1V2TlgzV3NDUXJHQUNOeXVnVXNtb3lMTHo3ZXlTU2pWZGxyVDRJTUljPSIsIml2UGFyYW1ldGVyU3BlYyI6InpxWlRkc0tTRWNHM0NxYlQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)    |
| kafka-utils    | ![kafka-utils](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiYlhETjU3U0dTWFpPb2srSlg0TllYOFJSdzBxOE8xSjRWRUVIU2FGVmM3TmNqSk8yOGZwWXUzdmtzNm43WXcwSWhkTmw5eE50TTNscVlNZCtPQlhCTTVJPSIsIml2UGFyYW1ldGVyU3BlYyI6IjRWS0xQbFU5K1VMU1dIZksiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)    |
| metrics-pusher | ![metrics-pusher](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiTDI4V0pMd1d6SkhCR3ZjMGZZOGZBMjdsaFlzY3NsVEdNYmVPc0JTeDFpanhUeG1wM2c2S1pTTkYrbWp5ZEU2K3JNdE9ZTW82aDFaOWhwSUdobTVkakVrPSIsIml2UGFyYW1ldGVyU3BlYyI6IkIxVldLQ0ExME8vTThadUwiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master) |
| puller         | ![puller](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiVmlwdGFWQm85UzhkTGpQeStnMTNPUVRQcklQWGZ1ZzB2SCtoRmRzam1FN0F0eVZCa242VEpGYzVicUlSdEFxeURTNkpiSFhjZ1ZwM1FERkNHZzFCWXBNPSIsIml2UGFyYW1ldGVyU3BlYyI6Ik1BcXJCRGxnK0xWSkZTcHQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)         |
| watcher        | ![watcher](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoibCs3cXVxUmx6ZkRGNDNaRlV4V3I4WkFuUk5DRDRzbFRldUJqNUpJVTc1RGswWHBFekwwSklVYThMM3VHSFhwTjNrR0RFd1dFanFSTzQrTk04V3locDYwPSIsIml2UGFyYW1ldGVyU3BlYyI6Ik5BQjJ3NEd3ZDRwY3VqNG4iLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)        |

# Quick start

## Step 0 - Requirements

1. Get AWS credentials on your environment variables.
   It can be either `AWS_PROFILE` or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.
   [This guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html) helps setting these
   variables (ignore the fact it says it's for the Java SDK).
1. Install [miniconda](https://docs.conda.io/en/latest/miniconda.html).
   

You are now ready to create the environment to use the tool:

```bash
git clone https://github.com/MXNetEdge/benchmark-ai.git
cd benchmark-ai/baictl
conda env update
conda activate baictl
./baictl.sh --help
``` 

If you want baictl.sh to be available as baictl in terminal do the following:

```
cd && mkdir -p work && cd work
git clone git@github.com:MXNetEdge/benchmark-ai.git

# choose or create a path on $PATH to put the link
cd && mkdir -p bin
echo 'export PATH=~/bin:$PATH' >> ~/.bashrc
ln -s ~/work/benchmark-ai/baictl/baictl.sh baictl

# install completion
echo 'source ~/work/benchmark-ai/baictl/baictl-complete.sh' >> ~/.bashrc
```

## Step 1 - Create the infrastructure

You will now create the whole BAI infrastructure in your AWS account using the default region us-west-2 (this can be changed from benchmark-ai/baictl/config.yml):

```bash
# Assuming PWD is `benchmark-ai/baictl`
./baictl-infrastructure.py create
```

After approximately 10 minutes the infrastructure should be created in your account. An example of output is:

```
Please enter the AWS_PROFILE name [Default: None]:
2019-07-02 13:24:01,958- INFO - Found credentials in shared credentials file: ~/.aws/credentials
2019-07-02 13:24:04,935- INFO - Building Docker image
2019-07-02 13:26:34,849- INFO - Updating CloudFormation stack: baictl-ecs
2019-07-02 13:26:35,267- INFO - No CloudFormation changes
2019-07-02 13:26:38,847- INFO - Publishing docker image, this might take ~15 minutes
2019-07-02 13:40:55,140- INFO - Executing infrastructure build on AWS Elastic Container Service
2019-07-02 13:40:55,954- INFO - Running ECS Task to create infrastructure
2019-07-02 13:40:56,880- INFO - Waiting for logs, this should take less than 60 seconds
2019-07-02 13:42:02,928- INFO - Cloudwatch log for run here: https://console.aws.amazon.com/cloudwatch/home?region=us-west-2#logEventViewer:group=baictl-ecs-baictl;stream=baictl/baictl/a3571780-fc1d-47fa-92b8-187bd130fa66
2019-07-02 13:42:03,654- INFO - Waiting for ECS task to finish...
2019-07-02 14:08:42,317- INFO - Complete!  Anubis infrastructure is ready
2019-07-02 14:08:42,319- INFO - Syncing ~/.bai directory with infrastructure details
```

As you probably guessed, under the hood, `baictl` is:

- Using [terraform](https://www.terraform.io/) to create all of the AWS infrastructure:
    - an [EKS](https://aws.amazon.com/eks) cluster
    - an [Elasticsearch](https://aws.amazon.com/elasticsearch-service/) cluster
- Adding some Pods to Kubernetes. Some of them are:
    - FluentD
    - Autoscaler
    - NVIDIA device plugin
    
**Advanced usage**: The directory `$HOME/.bai` is created with everything related to the infrastructure (terraform output, kubeconfig, etc.).  You can optionally specify $ANUBIS_HOME with your preferred path

## Step 2 - Run benchmarks

BAI provides some sample benchmarks at the `benchmark-ai/sample-benchmarks` directory. Let's run some of them:

```bash
# Assuming PWD is `benchmark-ai/baictl`
./baictl.sh run benchmark --descriptor=../sample-benchmarks/hello-world/descriptor.toml
```

By doing this you submitted a benchmark run to Benchmark AI (which is a [Kubernetes job](https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/) by the way),
and the following will be done:

- The descriptor file is read and validated.
- BAI submits a job to Kubernetes
- Kubernetes allocates node(s) for you (using [Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)).
- The benchmark runs, emitting metrics via the `emit()` method provided by the [client-lib](https://github.com/MXNetEdge/benchmark-ai/tree/master/client-lib).
- Logs are collected into:
    - Elasticsearch
- Metrics are collected into:
    - Elasticsearch

## Step 3 - Collect the results of your run

```bash
# Assuming PWD is `benchmark-ai/baictl`
./baictl.sh get benchmark --name=<BENCHMARK_ID>
```

## Great, what's next?

Write your own benchmarks!

Explore the [descriptor file format](https://github.com/MXNetEdge/benchmark-ai/tree/master/baictl/descriptor-file)
in order to run your benchmarks in Benchmark AI. Make sure to post metrics by integrating the [client library](https://github.com/MXNetEdge/benchmark-ai/tree/master/client-lib)
in your code.

Other interesting features:

- Cronjobs (https://github.com/MXNetEdge/benchmark-ai/issues/24)
- Distributed ML training benchmarks (https://github.com/MXNetEdge/benchmark-ai/issues/28)

# Design and architecture

TODO

# Supported cloud providers

- AWS