<!---
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
-->
# Inception Integration Tests


Docker in docker in docker... Oh my!

## Requirements

### What do I need to run integration tests on my local machine?

**Deprecated mid-term**: minikube is enough for a quick start. Since minikube of a reasonable version is a part of docker installation it can be enough unless you need multiple nodes
**Current state **Integration tests are getting more complex and we indeed need multiple nodes in some cases. We recommend you to adopt https://github.com/kubernetes-sigs/kind

### What’s the difference between minikube and kind?

|Feature    |minikube    |kind    |
|---    |---    |---    |
|Runs a node...    |as local docker environment    |as a container with docker-in-docker    |
|Repository is...    |your local repository    |the repository inside of either container    |

Good overview can be found here:
https://www.loodse.com/blog/2019-03-12-running-kubernetes-in-the-ci-pipeline-/

### Any other options?

We have evaluated https://github.com/kubernetes-retired/kubeadm-dind-cluster. The project is deprecated in favour of kind. Slower initialisation, not as closely smooth as kind.

For a moment we have considered running minikube with —vm-driver=none in docker. Although there are concept proofs, that it’s possible, we have found faking systemctl to be an unstable and tedious solution.
https://aspenmesh.io/2018/01/building-istio-with-minikube-in-a-container-and-jenkins/
Typical implementation:
https://github.com/testingtoollab/minikube-container
We have not seen any examples of a recent minikube version running with a recent k8s.

### How do I setup the kind cluster?

```
#Setup kind.
#Find the image for your kind and kubernetes version here:
#https://github.com/kubernetes-sigs/kind/releases
#Provide cluster config, if necessary - otherwise just one node will be used
export K8S_KINDEST_V12=\kindest/node:v1.12.9@sha256:bcb79eb3c...
kind create cluster --image=$K8S_KINDEST_V12 --config=integration-test-cluster.yml
export KUBECONFIG=$(kind get kubeconfig-path)

#Now we can use kubectl

#Label the nodes, as you need
kubectl label node kind-worker2 node.type=bai-services-cheap
```

## Running tests

### How do I run tests against kind?

```
# Set the stage
export STAGE=local
# Provide make publish with a replacement for docker push
export LOCAL_PUBLISH="kind load docker-image "
```

### Ok. How do I run tests at all?

```
#Predeploy the service you run tests against
make deploy

#Run them!
make integration tests
```

### Can I actually run integration tests against a real cluster?

Yes. Use

```
export STAGE=devo #Or prod
```

## Internals

### How is the test implemented?

The tests are executed in a container built with Docker-it dockerfile. That’s basically Docker-service + pytest.
That tests can be:

* Black-box tests executed against a service deployed to local cluster
* Integration tests of some parts of the service executed inside of the job - API Tests, boundary tests etc.

The build container is executed as job.

A typical test of the executor service may look like this:

```
# Send the event to be handled by the service
kafka_producer.send(BAI_APP_FETCHER, FetcherBenchmarkEvent("ACTION_ID"))

#Verify the k8s job was created
wait_for_k8s_job("ACTION_ID", running, SOME_TIMEOUT)

# Verify the executor has produced the output event
wait_for_executor_event(BAI_APP_EXECUTOR, SOME_TIMEOUT)

#Verify the job terminates
wait_for_k8s_job("ACTION_ID", terminated, SOME_TIMEOUT)
```

The integration test consumes from service’s producer and produces to the consumer.
[Image: it.png]

[Link](https://wsd.aka.amazon.com/?lz=CnBhcnRpY2lwYW50IFRlc3QgYXMgVAAJDUthZmthIGFzIEsAIA1FeGVjdXRvciBhcyBFCgpULT5UOiB0ZXN0X2V4ZWMKYWN0aXZhdGUgVApULT5LOiBzdGFydF9iZW5jaG1hcmsKSy0-RQAEEkUAIgplZApLAFAFAAYIZGUASwo&s=default&h=vGZCH4EYj082PWxn)

### Do we run tests against real S3 or MSK?

No. All the AWS dependencies are mocked inside of the mock-infra deployment.
We use containers with kafka/zookeeper/s3 (using https://hub.docker.com/r/zenko/cloudserver/)
It’s easy to imagine ElasticSearch

### Why do we run job inside of cluster?

**tl;dr  We were not able to expose Kafka in multiple networks**

Running the job inside of cluster has the following disadvantages:

* You need additional **kubectl logs **to collect the logs of the job
* You need some **kubectl get job **to get the status of the job at all (!)

If you can run it outside of the cluster in the pytest process - go for it.

To run tests outside of the cluster you have to expose all the services. Our immediate party stopper was Kafka. We are not able to expose Kafka in multiple networks with different names:
http://www.adaltas.com/en/2017/07/22/exposing-kafka-on-two-different-networks/

### Why does it take 10 seconds to run any test?

Integration test is a KafkaConsumer. It takes some time (seconds!) to settle a consumer group - 10s are P999 enough. Since we aim for a clean isolated execution of the tests, each test joins and leaves the cluster.

### What logs are dumped on failed integration tests?

We dump as much as possible:

* IT job
* Corresponding service
* Pods spawned by the service

Additionally we run **kubectl describe pods**
