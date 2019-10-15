#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="bai_fetcher_job",
    url="https://github.com/awslabs/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    entry_points={"console_scripts": ["start = bai_fetcher_job.__main__:main"]},
)
