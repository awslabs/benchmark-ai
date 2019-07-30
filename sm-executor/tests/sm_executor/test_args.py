from bai_kafka_utils.executors.descriptor import DescriptorConfig

from sm_executor.args import create_executor_config, SageMakerExecutorConfig

MOCK_SAGEMAKER_OUTPUT_BUCKET = "some_bucket"
MOCK_SAGEMAKER_ROLE = "some_role"
MOCK_NODATA_SET = "s3://some_bucket/nodata"
MOCK_TMP_DIR = "/tmp/dir"
MOCK_VALID_ENGINES = "e1,e2"
MOCK_VALID_STRATEGIES = "s1,s2"
MOCK_VALID_FRAMEWORKS = "f1,f2"
MOCK_SUBNETS = "n1,n2"
MOCK_SECURITY_GROUP_IDS = "sg1,sg2"

CMD_LINE = (
    f"--sagemaker-output-bucket={MOCK_SAGEMAKER_OUTPUT_BUCKET} "
    f"--sagemaker-role={MOCK_SAGEMAKER_ROLE} "
    f"--sagemaker-nodataset={MOCK_NODATA_SET} "
    f"--tmp-sources-dir={MOCK_TMP_DIR} "
    f"--valid-execution-engines={MOCK_VALID_ENGINES} "
    f"--transpiler-valid-frameworks={MOCK_VALID_FRAMEWORKS} "
    f"--transpiler-valid-strategies={MOCK_VALID_STRATEGIES} "
    f"--sagemaker-subnets={MOCK_SUBNETS} "
    f"--sagemaker-security-group-ids={MOCK_SECURITY_GROUP_IDS}"
)

MOCK_ENV = {
    "SAGEMAKER_OUTPUT_BUCKET": MOCK_SAGEMAKER_OUTPUT_BUCKET,
    "SAGEMAKER_ROLE": MOCK_SAGEMAKER_ROLE,
    "SAGEMAKER_NODATASET": MOCK_NODATA_SET,
    "TMP_SOURCES_DIR": MOCK_TMP_DIR,
    "VALID_EXECUTION_ENGINES": MOCK_VALID_ENGINES,
    "TRANSPILER_VALID_FRAMEWORKS": MOCK_VALID_FRAMEWORKS,
    "TRANSPILER_VALID_STRATEGIES": MOCK_VALID_STRATEGIES,
    "SAGEMAKER_SUBNETS": MOCK_SUBNETS,
    "SAGEMAKER_SECURITY_GROUP_IDS": MOCK_SECURITY_GROUP_IDS,
}

EXPECTED_SM_CONFIG = SageMakerExecutorConfig(
    valid_execution_engines=["e1", "e2"],
    tmp_sources_dir=MOCK_TMP_DIR,
    sm_role=MOCK_SAGEMAKER_ROLE,
    s3_output_bucket=MOCK_SAGEMAKER_OUTPUT_BUCKET,
    s3_nodata=MOCK_NODATA_SET,
    descriptor_config=DescriptorConfig(valid_frameworks=["f1", "f2"], valid_strategies=["s1", "s2"]),
    security_group_ids=["sg1", "sg2"],
    subnets=["n1", "n2"],
)


def test_config_cmdline():
    cfg = create_executor_config(CMD_LINE, {})
    assert cfg == EXPECTED_SM_CONFIG


def test_config_env():
    cfg = create_executor_config("", MOCK_ENV)
    assert cfg == EXPECTED_SM_CONFIG
