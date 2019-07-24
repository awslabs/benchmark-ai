import pytest

from bai_kafka_utils.executors.util import ec2_instance_info


def test_get_num_installed_gpus_valid_gpu():
    assert ec2_instance_info.get_instance_gpus(instance_type="p3.8xlarge") == 4


def test_get_num_installed_gpus_invalid_gpu():
    with pytest.raises(Exception):
        ec2_instance_info.get_instance_gpus(instance_type="p3.18000xlarge")


def test_get_num_installed_gpus_valid_cpu():
    assert ec2_instance_info.get_instance_gpus(instance_type="c5.18xlarge") == 0


def test_get_num_installed_gpus_invalid_cpu():
    assert ec2_instance_info.get_instance_gpus(instance_type="c5.18000xlarge") == 0
