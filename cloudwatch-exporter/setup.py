#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="cloudwatch_exporter",
    url="https://github.com/MXNetEdge/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"console_scripts": ["start=cloudwatch_exporter.__main__:main"]},
)
