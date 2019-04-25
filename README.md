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
|:---------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| baictl         | ![baictl](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiVS8vVlRqQ1RPT1EwTnNqZ0xtT20wZGNnaGNMUTI0Q25Sd0ltcFI5ZklaVm5IbWhQMnFtZHNLaGVpQXdwYmdrTld6cGlQMU9RSERTL01lSytiUmI3Nk9RPSIsIml2UGFyYW1ldGVyU3BlYyI6Im03RHZBdzBmZ1FHaEJDZTAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)         |
| client-lib     | ![client-lib](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiRG5sWDZmeEdScVJuaDZLMzZuUC8xU2taSFZVeTd4dkFjMk43THJTc1J6QldaSUpKQkNDSGxCSVV2VEJ1OHVsQ1IrcFgrV2lSN01rUWFYKysxS3NqN1BJPSIsIml2UGFyYW1ldGVyU3BlYyI6InZUOUNpWmVIWjNxVmloVTEiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)     |
| fetcher        | ![fetcher](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiczR0eGlwcnBPMEd2VEtBUzcrMy9VaWRmT3FjZ0xWeU9lZ25tUTY2c2lnYzNacWVVOE5uaWhXcEUzUzNLalQwcnBXSy9LQ2poa3AzTGpFalhIejhVUjNjPSIsIml2UGFyYW1ldGVyU3BlYyI6IkZSZi9KWURjaHVqcldCOVMiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)        |
| fetcher-job    | ![fetcher-job](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiSmRYdVZWSE1Yd05KVzBDM1lEL1MzVUJwaVprUmwxMmdLQVQwVWY4czFRb2JUK1V2TlgzV3NDUXJHQUNOeXVnVXNtb3lMTHo3ZXlTU2pWZGxyVDRJTUljPSIsIml2UGFyYW1ldGVyU3BlYyI6InpxWlRkc0tTRWNHM0NxYlQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)    |
| kafka-utils    | ![kafka-utils](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiYlhETjU3U0dTWFpPb2srSlg0TllYOFJSdzBxOE8xSjRWRUVIU2FGVmM3TmNqSk8yOGZwWXUzdmtzNm43WXcwSWhkTmw5eE50TTNscVlNZCtPQlhCTTVJPSIsIml2UGFyYW1ldGVyU3BlYyI6IjRWS0xQbFU5K1VMU1dIZksiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)    |
| metrics-pusher | ![metrics-pusher](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiTDI4V0pMd1d6SkhCR3ZjMGZZOGZBMjdsaFlzY3NsVEdNYmVPc0JTeDFpanhUeG1wM2c2S1pTTkYrbWp5ZEU2K3JNdE9ZTW82aDFaOWhwSUdobTVkakVrPSIsIml2UGFyYW1ldGVyU3BlYyI6IkIxVldLQ0ExME8vTThadUwiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master) |
| puller         | ![puller](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiVmlwdGFWQm85UzhkTGpQeStnMTNPUVRQcklQWGZ1ZzB2SCtoRmRzam1FN0F0eVZCa242VEpGYzVicUlSdEFxeURTNkpiSFhjZ1ZwM1FERkNHZzFCWXBNPSIsIml2UGFyYW1ldGVyU3BlYyI6Ik1BcXJCRGxnK0xWSkZTcHQiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)         |
| reports        | ![reports](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoidXQzU2lGRStuUjA3dHkwcmRmeHVCb2w5cmJGVWhSNUZRbzdoaVgzcytWUUk2WS9Fa28wbnVCL0k3K1h1YTlUb2Z1dkdlMUdrV0xKSnZ3M2tJL1pzZ0RnPSIsIml2UGFyYW1ldGVyU3BlYyI6Im1FcVErU2xzb1ZQUHZyNzkiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)        |  

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

You will now create the whole BAI infrastructure in your AWS account using the default region (eu-west-1):

```bash
# Assuming PWD is `benchmark-ai/baictl`
./baictl create infra
```

After approximately 10 minutes the infrastructure should be created in your account. An example of output is:

```
...
Apply complete! Resources: 50 added, 0 changed, 0 destroyed.

Outputs:

bastion_pem = bastion_private.pem
bastion_public_ip = 18.203.233.137
cluster_endpoint = https://769F05FC85C1A9F9429459726706DBE3.yl4.eu-west-1.eks.amazonaws.com
eks_cluster_name = benchmark-cluster
cluster_security_group_id = sg-0015597c89ae1cec8
config_map_aws_auth = <sensitive>
es_endpoint = vpc-logs-lcq7uzesgj43lpx3ob3t72e6tm.eu-west-1.es.amazonaws.com
kubectl_config = <sensitive>
region = eu-west-1

```

As you probably guessed, under the hood, `baictl` is:

- Using [terraform](https://www.terraform.io/) to create all of the AWS infrastructure:
    - an [EKS](https://aws.amazon.com/eks) cluster
    - an [Elasticsearch](https://aws.amazon.com/elasticsearch-service/) cluster
- Adding some Pods to Kubernetes. Some of them are:
    - FluentD
    - Autoscaler
    - NVIDIA device plugin
    
**Advanced usage**: The directory `$PWD/bai` is created with everything related to the infrastructure (terraform state, kubeconfig, etc.).

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
