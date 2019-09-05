A "framework/tool/service" that enables you to perform benchmarks of your machine learning models/frameworks/hardware in order to evaluate functionality, performance and detect regressions.


![how_good_is_uour_ml](docs/images/anubis.scales.jpg "Anubis")



Anubis provides a simple, self service solution for teams to schedule and run benchmarks for machine learning workloads.  Abubis lets teams to easily spin-up the required infrastructure and automation to perform benchmarks. Consider Anubis a measuring tool, a "ruler" if you willl, that lets you measure the efficacy of your machine learning model, framework and/or computing infrastructure.  Anubis provides a simple, declartive, input descriptor, and produces operational and user metrics, and sophisticated alerts for detecting regressions.  Logged output from the model are stored and indexed for deeper inspection, allowing for more effective root cause investigation.

# Features

* Simple _declarative_ _document-based_ input that gives user full control of Model / Framework / Hardware
* Simple command-line interface
* Strong Reproducibility
* Efficient Dataset Caching
* Ease of use and deployment
* Enables self-service model (anyone can spin up Anubis)
* Designed to be future proof
* Built around open standards
* Cloud native, cloud ready and cloud scalable*
* Operational Metrics

*Takes advantage of your cloud provider or datacenter's available resources - currently supports AWS out-of-the-box"



# Usage

<b>Anubis</b> provides <b>two</b> fundamental scripts.

One is the installer [`anubis-setup`](docs/anubis-setup.md), that is used to...

- configure and create the Anubis infrastructure

The other is the [`anubis`](bff/docs/anubis-client.md) client tool that allows users to...

- run a benchmark: `anbis --submit resnet50-descriptor.toml`
- monitor the progress of a run activities `anubis --status`
- obtain information from a benchmark that was run: `anubis --results`

The envisioned use-case is that a team or group or org instantiates the service infrastructure to be be used by its constituents. As such only the "admin" needs to run [`anubis-setup`](docs/anubis-setup.md).  While all users of Anubis interact with it using the `anubis` client tool.

For more information on how to use [`anubis-setup`](docs/anubis-setup.md), including use case examples and option explanations, please see the [full documentation here](docs/anubis-setup.md).<br>
For more information on how to use the [`anubis`](bff/docs/anubis-client.md) client, please see its [starter document](bff/docs/anubis-client.md).

<hr>
<i>
Why is it called "Anubis"? Because Anubis is the Egyptian God of the
afterlife. Anubis would weigh the goodness of your heart to decide if
you passed through to the after life. In this context, Anubis weighs
the goodness of your machine learning model, framework and
hardware. ;-)
</i>
<hr>

# Quick start

## Step 0 - Requirements

1. Get AWS credentials on your environment variables.
   It can be either `AWS_PROFILE` or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.
   [This guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html) helps setting these
   variables (ignore the fact it says it's for the Java SDK).
2. We use [CONDA](https://docs.conda.io/en/latest/index.html) as our way to stabilize the environment in which we run code.  Please install CONDA, the recommended installation is posted [here](https://docs.conda.io/en/latest/miniconda.html).
3. Install **bash** version 5+

After you have installed these tools, please open up a new terminal (the simplest way to come up in a clean new state).<br>
*Note - If your shell session comes up with the default "(base)" conda environment, deactivate the "(base)" environment with the following command:*

```bash
conda deactivate
```

Now, you are now ready to proceed :-)

```bash
git clone https://github.com/MXNetEdge/benchmark-ai.git
cd benchmark-ai
```


## Step 1 - Create the infrastructure

#### Overview...
The installation process... consists of two phases - 1) configuring and deploying *infrastructure* services, and then 2) configuring and deploying *orchestration* services.

**Infrastructure**:
- Uses [Terraform](https://www.terraform.io/) to create all of the infrastructure:
    - Kubernetes - [EKS](https://aws.amazon.com/eks) cluster
    - [Elasticsearch](https://aws.amazon.com/elasticsearch-service/) cluster
    - Kafka - [MSK](http://aws.amazon.com/msk) cluster
    - [Prometheus](https://prometheus.io/) broker and Alert Manager
- Adds Pods to Kubernetes:
    - FluentD
    - Autoscaler
    - NVIDIA device plugin

**Orchestration services**:
 - BFF
 - Fetcher
 - Executor
 - Watcher
----

### Installation Options:

#### Via Code Pipeline (recommended)

You will now create a Codebuild pipeline that deploys Anubis infrastructure and orchestration services in your AWS account using the default region us-east-1 (this can be changed from benchmark-ai/ci/variables.tf):

```bash
# Assuming PWD is `benchmark-ai`
./anubis-setup --region us-east-1 --prefix-list-id pl-xxxxxxxx
```

Type 'yes' when prompted and terraform will create the Codebuild pipeline and its dependencies.  When terraform finishes navigate to the AWS console -> Codebuild -> Pipeline -> Pipelines -> Anubis on the console to see the status of the installation

<details><summary>More about anubis-setup arguments</summary>
<p>

 - region: (REQUIRED) AWS region that Anubis infrastructure and services will be instantiated in.  There can only be one instantiation of Anubis per account due to IAM role name collisions, etc.
 - prefix-list-id: (REQUIRED) In order to access Anubis infrastructure from corp we can add the corresponding corp prefix list from the Amazon Prefix List Lookup tool
 - extra-users: *Provide as comma delimited list arn:aws:iam::1234:user/user1,arn:aws:iam::1234:user/user2* In order for a user to directly run kubectl commands against the Anubis EKS cluster you must provide that user's IAM ARN.  By default the users that are added are the Codebuild pipeline user, and your current aws user (find this out by running `aws sts get-caller-identity`)
 - extra-roles: Same as extra-users except with AWS IAM roles
 - github-organization / github-branch: To point the pipeline to track a branch other than master, good for personal pipeline development
 - chime-hook-url: Provide a chime URL for notification of pipeline failures
 - clean: Deletes the terraform statefile, backend config, terraform variable file, and terraform plan file.  Useful for debugging failures or resetting configuration.
 - destroy: Deletes Anubis infrastructure and pipeline

</p>
</details>

##### Get the service endpoint for Anubis

Once the Anubis pipeline has completed, at least the `deploy` step, successfully you need to query the EKS cluster for the Anubis service endpoint.

```bash
# Assuming PWD is `benchmark-ai`
cd baictl
./baictl sync infra --aws-region=us-east-1 --mode=pull
# The kubeconfig will be downloaded to `drivers/aws/cluster/.terraform/bai/kubeconfig`
kubectl --kubeconfig=drivers/aws/cluster/.terraform/bai/kubeconfig get service bai-bff -o json | jq '.status.loadBalancer.ingress[].hostname'
```

**OR**

#### Via the "no frills" instantiation

This form also does a full instantiation of the Anubis service (infrastructure and orchestration services).  However, with this installation mechanism you will **not** get any of the CI/CD benefits provided by code pipeline.  This means that to apply any updates you would have to do so explicitly by re-issuing the command or by using the appropriate flags that give you control down to the service level ([see documentation for more details](docs/anubis-setup.md)).  The "no frills" option is more high touch, and as such offers a bit more control over what services get updated, when and how.

``` bash
# Assuming PWD is `benchmark-ai`
pushd baictl
./baictl create infra --aws-region={region} --aws-prefix-list-id={matching prefix list}
popd
./bin/build-and-deploy-all-services
```

<details><summary>(advanced usage)</summary>
<p>
The directory `baictl/drivers/aws/cluster/.terraform/bai` is created with everything related to the infrastructure (kubeconfig, bastion_private.pem, etc.).
</p>
</details>

----

#### Registration:

Once the instantiation of the anubis *infrastructure* is complete you may begin to use the [`anubis`](bff/docs/anubis-client.md) client to interact with the system.  However, you must first tell the [`anubis`](bff/docs/anubis-client.md) client which infrastructure it needs to point to. You do this by *registering* your infrastructure's *endpoint* with the client.  Use the **--register** flag supplying the network **address** and **port** of your Anubis instantiation.  This will be provided to you at the end of the infrastructure instantiation process that you just went through (above).

``` bash
# Assuming PWD is `benchmark-ai`
bff/bin/anubis --register xxxxxxxxxxx-xxxx.us-east-1.elb.amazonaws.com:80
```

To check that the client has registered with the Anubis instantiation, **--ping** it.

``` bash
# Assuming PWD is `benchmark-ai`
bff/bin/anubis --ping

                       _      _
                      | |    (_)
   __ _  _ __   _   _ | |__   _  ___
  / _  ||  _ \ | | | ||  _ \ | |/ __|
 | (_| || | | || |_| || |_) || |\__ \
  \__,_||_| |_| \__,_||_.__/ |_||___/ ♎

(v0.1.0-481dad2)
-------------------------
AWS: Benchmark AI Client
-------------------------

Brought to you by the cool peeps of the  MXNet-Berlin Team
..........
Current service endpoint is: [xxxxxxxxxxx-xxxx.us-east-1.elb.amazonaws.com:80]

😎  Ready And Willing like Big Daddy Kane

```
This means you are good to go ;-) - Nice work.


## Step 2 - Run benchmarks

To run benchmarks and generally interact with Anubis, use the [Anubis client tool](bff/bin/anubis) ([starter doc here](bff/docs/anubis-client.md)).

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

*hint: put bff/bin/anubis, or symlink to it, in your $PATH*

Anubis supports "Script Mode".  This means along with posting the descriptor file, you may also specify and include the actual code that you wish to run.  This is a great way to more explicitly separate your model code from the framework you want to run. See our "Hello World" [README](sample-benchmarks/hello-world) for info on that.  Also look at the `anubis` client program [document](bff/docs/anubis-client.md) located in the bff service.

```bash
#To watch the status messages showing the progress of the run
bff/bin/anubis --watch --status
```



## Step 3 - Collect the results of your run

```bash
# Assuming PWD is `benchmark-ai`
bff/bin/anubis --results <ACTION_ID>
```

## Step 4 - Destroy Anubis Infrastructure

```bash
# Assuming PWD is `benchmark-ai`
./anubis-setup --region us-east-1 --prefix-list-id pl-xxxxxxxx --destroy
```

*Note - There is a bug in terraform where security group don't get revoked before security group deletion causing timeout https://github.com/hashicorp/terraform/issues/8617*

## Great, what's next?

Write your own benchmarks!

Explore the [descriptor file format](executor/README.md)
in order to run your benchmarks in Benchmark AI. Make sure to post metrics by integrating the [client library](https://github.com/MXNetEdge/benchmark-ai/tree/master/client-lib)
in your code.

Future Feature Roadmap...

<details><summary>Global status state</summary>
<p>

To be able to store status state in a global store that persists.  In
the current implementation the data is stored in memory and is
ephemeral bound to the life-cycle of the BFF instance(s).  The solution here is to use a data structure store.  Redis would be a suitable tool for this.  One may also just take advantage of the event persistence story, and replenish data from Kafka or S3.

</p>
</details>
<details><summary>User Metrics</summary>
<p>

To provide user defined metrics to the customer.  This entails
providing a means of dynamically producing dashboards for a given run
based on what is being collected/emitted.

</p>
</details>

<details><summary>AWS: Cloudwatch exporting</summary>
<p>

To export data so that it may be consumed by cloudwatch.  This entails
creating a service whose function is to listen to messages and writing
them out to Cloud Watch.

</p>
</details>
<details><summary>AMI Support</summary>
<p>

For Anubis to support running jobs across "bare metal" AMIs.

This feature can be supported in three phases.
<ul>
<li> Implementing an executor that can provision EC2 instances and imbue them with software to coordinate runs. The first pass would be running single node jobs.
<li> Following that is setting up for multi-node jobs
<li> Finally, addressing the alerting story in this context.
</ul>

</p>
</details>
<details><summary>Alerting</summary>
<p>

With regards to metrics, we want to be able to alert the user if there
are exceptional conditions based on the metrics values.  This is
allows the system to be used for regression detection among other
things.  Anubis sets up Prometheus as well as the Prometheus Alert
Manager. We will directly leveraged it to satisfy all reasonable
alerting needs.  The trick here is to figure out how to capture the
alerting rules. This may, most likely, be written as a new stanza in
the TOML.

</p>
</details>
<details><summary>AWS: Improved AZ selection</summary>
<p>

Availability Zones can be specified explicitly in the TOML descriptor,
if not they are randomly selected.  The random selection could lead to
running pods in zones that don't have the resources desired.  This
leads to the system not being able to run a benchmark, and spinning
forever waiting for resources that are not present and never
returning.  The low hanging fruit here would be to set a max timeout
threshold for waiting on resources.  The better solution would be to
connect to an API (or some information) where you can determine that
the resources desired are present.

</p>
</details>
<details><summary>Range capabilities in TOML</summary>
<p>

We want to be able to specify ranges of values across the *framework*,
*model*, *hardware* axes.  This would generate the cross product of
results. This would be especially useful in the hyper parameter
optimization space.  This feature would require the introduction of an
aggregating identifying attribute that would group action ids into an
"action-id-family" With the action-id-family, the notion of experiment
can be realized - as a set of actions / runs that are semantically
related.

</p>
</details>
<details><summary>Persistent metrics, raw events and log storage</summary>
<p>

Being able to have all events recorded durably would be advantageous
as it would result in having "event datasets" that enable further
out-of-band investigations or reporting.

<ul>

<li> Events: Listen to Kafka and dump all the events for each topic to
S3.
<li> Logs: We are using fluentD to push logs to ElasticSearch. This
can be configured to write to s3 (I believe - need to confirm)
<li> Metrics: This means having a persistence story for Prometheus
metrics which are rather opaque and not amenable to simple file
writing.  There is a story and write up for this capability, executing
it will manifest this feature.
</ul>
</p>
</details>
<details><summary>Report generation</summary>
<p>

Processing systems to generate reports akin to those presented now
with "BAI 1.0".  Report generation entails looking through data to put
together the insights you seek.  This is largely out-of-band
processing happening at the egress end of the system, and goes hand in
hand with the raw persistence story.

</p>
</details>

# Design and architecture

The system is built to embody a few guiding tenets:

<ul>
  <li>Self Service</li>
  <li>"Push Button" Installation</li>
  <li>Complete Delivery</li>
  <li>Clear Mental Model (Transparency)</li>
  <li>Use best of breed technology that has significant mind share</li>
</ul>

The picture below shows the "infrastructure" layer of Anubis.

![Anubis design](docs/images/anubis_architecture_diagram.png "Anubis Design")

The orchestration layer consists of services running on K8s, sending
[events](docs/anubis-event-design.md#benchmark-ai-event-design) to
each other to coordinate the activities necessary to shepherd model
runs. More specifically events are sent to kafka on specified topics.
Kafka facilitates the event sending throughout Anubis.


#### Technologies

This project is an exercise in the amalgamation and orchestration of several technologies to create a tool that adds value to our users.

- Python: (https://www.python.org/)
- Clojure: (https://clojure.org/),  (https://www.braveclojure.com/do-things/)
- Bash: (https://www.tldp.org/LDP/abs/html/)
- Jq: (https://stedolan.github.io/jq/)
- Conda: (https://docs.conda.io/projects/conda/en/latest/index.html)
- Docker: (https://www.docker.com/)
- Kafka: (http://kafka.apache.org/intro) (MSK)
- Kubernetes: (https://kubernetes.io/) (EKS)
- Prometheus: (https://prometheus.io/)
- Terraform: (https://www.terraform.io/)
- Zookeeper: (https://zookeeper.apache.org/)
- ElasticSearch: (https://www.elastic.co/products/elasticsearch) (Managed ElasticSearch)

# Supported cloud providers
(currently)
- AWS
