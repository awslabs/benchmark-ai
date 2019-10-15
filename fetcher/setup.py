#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="fetcher_dispatcher",
    url="https://github.com/awslabs/benchmark-ai",
    package_dir={"": "src"},
    requires=["bai_kafka_utils"],
    packages=find_packages("src"),
    include_package_data=True,
    entry_points={"console_scripts": ["start=fetcher_dispatcher.__main__:main"]},
)
