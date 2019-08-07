A "framework" that enables to periodically generate performance benchmarks of Machine Learning systems in order to evaluate new functionalities and detect regressions.


![how_good_is_uour_ml](docs/images/anubis.scales.jpg "Anubis")

# A "framework" ?

Anubis provides a simple, self service solution for teams to schedule and run benchmarks for Machine Learning systems.
It allows teams to spin-up the required infrastructure and automation needed to perform benchmarks. Using Anubis,
users can monitor the evolution of their benchmarks over time to detect anomalies or regressions. Alarms can be
configured to notify the corresponding teams when certain metrics exceed given thresholds.

# Usage

<b>Anubis</b> provides <b>two</b> fundamental scripts.

One is the `baictl` (BAI = Benchmark AI, ctl = control...clever huh!) utility.
It is used to...

- create the service infrastructure: `baictl create infra`

The other is the `anubis` client tool that allows users to...

- run a benchmark: `anbis --submit resnet50-descriptor.toml`
- monitor the progress of a run activities `anubis --status`
- obtain information from a benchmark that was run: `anubis --results`

The envisioned use-case is that a team or group or org instantiates the service infrastructure to support its constituents.  As such only the "admin" needs to run `baictl`.  While all users of the service interact with it using the Anubis client tool (or via the direct HTTP API, for the adventurous)

For more information on all commands, please see the [full documentation]() of `baictl`.<br>
For more information on the `anubis` client, please see its [starter document](bff/doc/anubis-client.md).

<hr>
<i>
Why is it called "Anubis"? Because Anubis is the Egyptian God of the
afterlife. Anubis would weigh the goodness of your heart to decide if
you passed through to the after life. In this context, Anubis weighs
the goodness of your machine learning model, framework and
hardware. ;-)
</i>
<hr>

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


You are now ready to create the environment to use the tool:

```bash
git clone https://github.com/MXNetEdge/benchmark-ai.git
cd benchmark-ai
```

## Step 1 - Create the infrastructure

**NOTE**: These steps will soon be replaced by a wrapper script to make your life easier! 

You will now create a Codebuild pipeline that deploys Anubis infrastructure and services in your AWS account using the default region us-east-1 (this can be changed from benchmark-ai/ci/variables.tf):

```bash
# Assuming PWD is `benchmark-ai`
cd ci
conda env update && conda activate ci
./terraform-init.py
terraform apply
```

Type 'yes' when prompted and terraform will create the Codebuild pipeline and its dependencies.  When terraform finishes navigate to the AWS console -> Codebuild -> Pipeline -> Pipelines -> Anubis on the console to see the status of the installation

As you probably guessed, under the hood, the CreateInfra stage is using `baictl` which is:

- Using [terraform](https://www.terraform.io/) to create all of the AWS infrastructure:
    - an [EKS](https://aws.amazon.com/eks) cluster
    - an [Elasticsearch](https://aws.amazon.com/elasticsearch-service/) cluster
    - a [MSK](http://aws.amazon.com/msk) cluster
    - a  [Prometheus](https://prometheus.io/) broker and Alert Manager
- Adding some Pods to Kubernetes. Some of them are:
    - FluentD
    - Autoscaler
    - NVIDIA device plugin

And the Deploy stage is running `make deploy` on the various services:
 - Executor
 - Fetcher
 - Watcher
 - BFF
 - ...

**Advanced usage**: The directory `baictl/drivers/aws/cluster/.terraform/bai` is created with everything related to the infrastructure (kubeconfig, bastion_private.pem, etc.).

## Step 2 - Run benchmarks

Anubis provides some sample benchmarks at the `benchmark-ai/sample-benchmarks` directory. Let's run some of them:

```bash
# Assuming PWD is `benchmark-ai`
bff/bin/anubis --submit sample-benchmarks/hello-world/descriptor.toml
```

By doing this you submitted a benchmark run to Anubis (which is a [Kubernetes job](https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/) by the way),
and the following will be done:

- The descriptor file is read and validated.
- Anubis submits a job to Kubernetes
- Kubernetes allocates node(s) for you (using [Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)).
- The benchmark runs, emitting metrics via the `emit()` method provided by the [client-lib](https://github.com/MXNetEdge/benchmark-ai/tree/master/client-lib).
- Logs are collected into:
    - ElasticSearch
- Metrics are collected into:
    - Prometheus

Optional: Put bff/bin/anubis in your $PATH

Anubis supports "Script Mode".  This means along with posting the descriptor file, you may also include the code that you wish to run.  See our "Hello World" [README](sample-benchmarks/hello-world) for info on that.  Also look at the `anubis` client program [document](bff/doc/anubis-client.md) located in the bff service.

```bash
#To watch the status messages showing the progress of the run
bff/bin/anubis --watch --status
```



## Step 3 - Collect the results of your run

```bash
# Assuming PWD is `benchmark-ai`
bff/bin/anubis --results <ACTION_ID>
```

## Great, what's next?

Write your own benchmarks!

Explore the [descriptor file format](executor/README.md)
in order to run your benchmarks in Benchmark AI. Make sure to post metrics by integrating the [client library](https://github.com/MXNetEdge/benchmark-ai/tree/master/client-lib)
in your code.

Other interesting features:

- Cronjobs (https://github.com/MXNetEdge/benchmark-ai/issues/24)
- Distributed ML training benchmarks (https://github.com/MXNetEdge/benchmark-ai/issues/28)

# Design and architecture

TODO

# Supported cloud providers

- AWS
