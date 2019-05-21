#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="prometheus-kafka-topic-exporter",
    url="https://github.com/MXNetEdge/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"util": ["ec2_instance_info.csv"], "executor": "*.yaml", "transpiler.templates": "*.yaml"},
    entry_points={"console_scripts": ["executor=executor.__main__:main"]}, # TODO
)
