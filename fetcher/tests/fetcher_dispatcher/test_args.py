from fetcher_dispatcher.__main__ import get_args

REQUIRED_ARGS = "--consumer-topic C --producer-topic P --s3-data-set-bucket S3"


def test_json_arg():
    args = get_args(REQUIRED_ARGS + ' --fetcher-job-node-selector={"node.type":"foo"}')
    assert args.fetcher_job_node_selector == {"node.type": "foo"}
