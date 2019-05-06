from fetcher_dispatcher.args import get_fetcher_service_config, FetcherServiceConfig, FetcherJobConfig

MOCK_S3_BUCKET = "s3://something"

EXPECTED_NODE_SELECTOR = {"node.type": "foo"}

MOCK_DOCKER_IMAGE = "docker/image"

MOCK_ZOOKEEPER_ENSEMBLE = "ZE1,ZE2"

MOCK_KUBECONFIG = "/path/kubeconfig"

MOCK_PULL_POLICY = "Always"

ALL_ARGS = (
    f"--s3-data-set-bucket={MOCK_S3_BUCKET} "
    f"--fetcher-job-image={MOCK_DOCKER_IMAGE} "
    f"--zookeeper-ensemble-hosts={MOCK_ZOOKEEPER_ENSEMBLE} "
    f"--kubeconfig={MOCK_KUBECONFIG} "
    '--fetcher-job-node-selector={"node.type":"foo"} '
    f"--fetcher-job-pull-policy={MOCK_PULL_POLICY}"
)

EXPECTED_CFG = FetcherServiceConfig(
    zookeeper_ensemble_hosts=MOCK_ZOOKEEPER_ENSEMBLE,
    s3_data_set_bucket=MOCK_S3_BUCKET,
    kubeconfig=MOCK_KUBECONFIG,
    fetcher_job=FetcherJobConfig(
        node_selector=EXPECTED_NODE_SELECTOR, image=MOCK_DOCKER_IMAGE, pull_policy=MOCK_PULL_POLICY
    ),
)


def test_get_cfg():
    cfg = get_fetcher_service_config(ALL_ARGS)
    assert cfg == EXPECTED_CFG


def test_dont_fail_unrecognized():
    get_fetcher_service_config(ALL_ARGS + " -foo")
