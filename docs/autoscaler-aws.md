The purpose of this document is to explain how the [Kubernetes cluster-autoscaler](https://github.com/kubernetes/autoscaler)
is being used in BAI.

It explains how we deal with the relationship between the Kubernetes autoscaler, AWS Auto Scaling Groups and BAI's setup
of these components. 

# Pre-requisites for understanding this document

Please read the following documents:
- [FAQ for AWS](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/cloudprovider/aws)
- [FAQ](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md)

Some familiarity with [AWS Auto Scaling Groups](https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html)
is beneficial, but not required.

Acronyms:
- BAI: Benchmark AI
- ASG: [AWS Auto Scaling Groups](https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html)
- CA: [Kubernetes cluster-autoscaler](https://github.com/kubernetes/autoscaler)
- K8S: Kubernetes
- AZ: AWS Availability Zone

# Setup

## Auto discovery

CA is setup in "Auto-Discovery" mode. When it starts up it will autodiscover the ASGs available for it to use. This 
setup is done with this flag on the [CA yaml](https://github.com/MXNetEdge/benchmark-ai/blob/master/baictl/drivers/aws/cluster/template/cluster-autoscaler-autodiscover.tpl.yaml):

```
--node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,kubernetes.io/cluster/${cluster_name}
```

The discovery of ASGs by the CA is done constantly (every few seconds), so it knows which ASGs can be used to spin up
new instances.

In order for the CA to be able to list the ASGs, IAM Permissions are given to the nodes.

Both of these requirements (tags and IAM permissions) are handled by the official [Terraform EKS module](https://github.com/terraform-aws-modules/terraform-aws-eks),
no action needs to be done on our side.

## The `node.type` label

There are 3 types of K8S nodes in BAI:

- `bai-worker`: Run the benchmark themselves.
- `k8s-services`: Run critical K8S services (eg.: CA, coredns, etc.). Typically deployments that run on the `kube-system`
                  namespace.
- `bai-services`: Run services that compose the BAI system (eg.: datafetcher, executor, etc.).

Each of these is the label `node.type` which is applied on the node by the Kubelet when they join the cluster. The label
is added through an extra Kubelet parameter, specified in Terraform: `--node-labels=node.type=bai-worker`.

Each Deployment/Job/MPIJob should then use the correct `node.type`.


## Restrict scheduling on specific availability zones

A [gotcha](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/cloudprovider/aws#common-notes-and-gotchas)
from cluster-autoscaler's AWS FAQ is particularly interesting:

> Cluster autoscaler does not support Auto Scaling Groups which span multiple Availability Zones; instead you should use
an Auto Scaling Group for each Availability Zone and enable the --balance-similar-node-groups feature. If you do use a
single Auto Scaling Group that spans multiple Availability Zones you will find that AWS unexpectedly terminates nodes
without them being drained because of the rebalancing feature. 

This talks about the "rebalancing" feature of ASG, which means that if we want to restrict the availability zone that
a Pod will run then we need to create 1 ASG per subnet. Given that it is also desired to control the instance type of
the nodes, then the amount of ASGs in total will be:

```
Number of availability zones used * Number of instance types 
```

Reasons to restrict the availability zone where Pods will run:
1. An availability zone might not have the specified instance type (eg.: P3 instances are not available in all AZs). The 
   error message is:
   ```
   The requested instance type is not supported in the requested availability zone
   ```
2. An availability zone might be running low on the amount of the specified instance type (eg.: low number of P3
   instances available).
   The [InsufficientInstanceCapacity error](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/troubleshooting-launch.html#troubleshooting-launch-capacity)
   message is:
    ```
    We currently do not have sufficient m4.4xlarge capacity in the Availability Zone you requested (ap-northeast-1d).
    Our system will be working on provisioning additional capacity. You can currently get m4.4xlarge capacity by not
    specifying an Availability Zone in your request or choosing ap-northeast-1c, ap-northeast-1a.`).
    ```
3. Minimize inter-az communication for distributed benchmarks: Lower latency and less cost.

Given that we want to maximize all of the above points, it makes sense to use **ALL** availability zones in the region
that BAI is being created. This might lead to another problem where the number of ASGs increase to a very high number
and reach the [limit](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html) of maximum 200 ASGs per
region, so a limit increase request might be required if not careful. 

# Scaling up (adding new nodes)

Every 10 seconds CA looks for Pods that failed to be scheduled (ie: it is **reactive**). When it notices a Pod failed to be
scheduled to a Kubernetes node, it will check if any of the ASGs satisfy that specific Pod requirement. If an ASG is
found, then it sets the `desired` property of the ASG and waits for the node to join the K8S cluster.

A Pod that failed to be scheduled to a node and is picked up for scheduling will look like this:

```
$ kubectl describe pod a681147f88f840769f11efc915fc0519-cq6km

  Type     Reason            Age                From                Message
  ----     ------            ----               ----                -------
  Warning  FailedScheduling  14s (x2 over 14s)  default-scheduler   0/3 nodes are available: 3 node(s) didn't match node selector.
  Normal   TriggeredScaleUp  3s                 cluster-autoscaler  pod triggered scale-up: [{benchmark-cluster-bai-worker.t2.small20190401093541701000000012 0->1 (max: 3)}]
```

## CA choosing the correct ASG to comply with `nodeSelector`

When CA is scanning the ASGs, it looks for tags in the ASG with the prefix `k8s.io/cluster-autoscaler/node-template/`
and takes them into consideration when choosing which ASG to use in order to scale up.

For example, if there is an ASG with the tag `k8s.io/cluster-autoscaler/node-template/node.type = bai-worker` and a Pod
with the following configuration is scheduled to run:

```yaml
nodeSelector:
    node.type: bai-worker
```

Then CA is able to choose the correct ASG to launch new nodes.

These are the mechanisms used in BAI to restrict which nodes a Pod can run on:

| Restriction mechanism | Label                                    | How does the Kubelet add this label? |
|:----------------------|:-----------------------------------------|:-------------------------------------|
| AZ restriction        | `failure-domain.beta.kubernetes.io/zone` | Automatically added by AWS provider  |
| Node type             | `node.type`                              | Setup in Terraform                   |


# Scaling down

The [section on the FAQ](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/FAQ.md#how-does-scale-down-work)
explains in detail how it works.

Given that `bai-worker` nodes will always run 1 Pod for a benchmark at a time, then the node is either **full** or
**empty**. Which makes this property of CA very desirable:

> Empty nodes, on the other hand, can be deleted in bulk, up to 10 nodes at a time

To delete a node, CA will always pick the specific nodes that can be scaled down. It doesn't leave that decision to the
ASG, which would pick a random node. My guess is that they "protect" instances that are running and "unprotect" them
when scale down can occur (see: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-termination.html).
On my tests, the cluster-autoscaler picked the correct nodes for termination.

## What about PodDisruptionBudget?

Kubernetes has this nice feature [PDB](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/#how-disruption-budgets-work)
which CA has support to, so it doesn't take down a Node that is running at the moment.

TODO: Study if this is necessary or helps in BAI's scenario. My guess is that BAI doesn't need this feature because
      it has this nice property of worker nodes being either **full** or **empty**.

# Gotchas

## cluster-autoscaler version and Kubernetes version

**If BAI is running Kubernetes > 1.12, then delete this section**

As stated in the [document](https://github.com/MXNetEdge/benchmark-ai/blob/master/docs/upgrading-kubernetes-version.md)
describing what to consider when upgrading Kubernetes, the version of cluster-autoscaler is dependant on the
Kubernetes version.

Currently BAI is [running version 1.12](https://github.com/MXNetEdge/benchmark-ai/blob/master/baictl/drivers/aws/cluster/variables.tf#L57)
(check the `k8s_version` terraform variable).

The version of CA that supports Kubernetes 1.12 is `1.12.X` and these versions have problem when dealing with more than
50 ASGs (this [commit](https://github.com/kubernetes/autoscaler/commit/e29bddc48331d396818065d0eccc8b1f3d9dd562) fixes
it). This commit is not present as of 11/Apr/2019 in the `1.12.X` versions:

```bash
$ git tag --contains e29bddc48331d396818065d0eccc8b1f3d9dd562
cluster-autoscaler-1.13.0
cluster-autoscaler-1.13.0-alpha.1
cluster-autoscaler-1.13.0-rc.2
cluster-autoscaler-1.13.1
cluster-autoscaler-1.13.2
cluster-autoscaler-1.14.0
cluster-autoscaler-1.14.0-beta.1
cluster-autoscaler-1.14.0-beta.2
```

So it was opted to use a newer version, although it is not using the supported K8S version.

If the cluster-autoscaler Pod behaves unexpectedly, then this might be the root cause.
