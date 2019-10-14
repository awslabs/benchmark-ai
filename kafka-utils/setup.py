#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from os.path import join, abspath, dirname

from setuptools import find_packages, setup

here = abspath(dirname(__file__))
bai_project_path = abspath(join(here, os.pardir))

setup(
    description="Shared library for kafka-based services",
    name="kafka_utils",
    url="https://github.com/MXNetEdge/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={
        "bai_kafka_utils.executors.util": ["ec2_instance_info.csv"],
    },
    include_package_data=True,
)
