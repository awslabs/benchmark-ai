import textwrap

import pytest

from descriptor_reader import KubernetesRootObjectHelper


@pytest.fixture
def k8s_job():
    return KubernetesRootObjectHelper(textwrap.dedent("""\
        apiVersion: batch/v1
        kind: Job
        metadata:
          name: job-id
        spec:
          template:
            metadata:
              labels:
                app: benchmark-ai
            spec:
              affinity:
                podAntiAffinity:
                  requiredDuringSchedulingIgnoredDuringExecution:
                  - labelSelector:
                      matchExpressions:
                      - key: app
                        operator: In
                        values:
                        - benchmark-ai
                    topologyKey: kubernetes.io/hostname
              initContainers: {}
              containers:
              - name: benchmark
                image: my-docker-image
                volumeMounts: {}
              nodeSelector:
                beta.kubernetes.io/instance-type: {instance_type}
              restartPolicy: Never
              volumes: {}
          backoffLimit: 4
    """))


def test_build_job(k8s_job):
    assert k8s_job._root.metadata.name == "job-id"


def test_find_container(k8s_job):
    container = k8s_job.find_container("benchmark")
    assert container.name == "benchmark"
    assert container.image == "my-docker-image"


def test_find_container_that_is_not_present(k8s_job):
    with pytest.raises(ValueError):
        k8s_job.find_container("container-not-on-pod")


def test_get_pod_spec(k8s_job):
    pod_spec = k8s_job.get_pod_spec()
    assert pod_spec.restartPolicy == "Never"


def test_build_job_without_pod():
    with pytest.raises(ValueError) as e:
        KubernetesRootObjectHelper(textwrap.dedent("""\
            apiVersion: batch/v1
            kind: Job
            metadata:
              name: job-id
            spec:
              template:
                metadata:
                  labels:
                    app: benchmark-ai
              backoffLimit: 4
        """))
    assert e.match("Pod not found at yaml definition of the Kubernetes object")


def test_build_job_where_pod_does_not_have_containers():
    with pytest.raises(ValueError) as e:
        KubernetesRootObjectHelper(textwrap.dedent("""\
            apiVersion: batch/v1
            kind: Job
            spec:
              template:
                spec:
                  containers: {}
        """))
    assert e.match("A Pod must have at least 1 container on its definition")


def test_build_job_without_spec():
    with pytest.raises(ValueError) as e:
        KubernetesRootObjectHelper(textwrap.dedent("""\
            apiVersion: batch/v1
            kind: Job
            metadata:
              name: job-id
        """))
    assert e.match("Spec of root object not found at yaml definition of the Kubernetes object")


def test_adds_placeholder_fields():
    """
    Some fields are not REQUIRED to be present in the input YAML, but they are created with empty fields if they're
    not present:

    For the Pod spec:
    - initContainers
    - volumes

    For each container:
    - volumeMounts
    """
    k8s_job = KubernetesRootObjectHelper(textwrap.dedent("""\
        apiVersion: batch/v1
        kind: Job
        spec:
          template:
            spec:
              containers:
              - name: benchmark
                image: my-docker-image
    """))
    assert k8s_job.get_pod_spec().volumes == []
    assert k8s_job.get_pod_spec().initContainers == []
    assert k8s_job.find_container("benchmark").volumeMounts == []
