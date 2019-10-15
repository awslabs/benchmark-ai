#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="sm_executor",
    url="https://github.com/awslabs/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"console_scripts": ["start=sm_executor.__main__:main"]},
)
