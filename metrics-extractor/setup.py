#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

setup(
    name="anubis-metrics-extractor",
    url="https://github.com/awslabs/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    entry_points={"console_scripts": ["start = anubis_metrics_extractor.__main__:main"]},
)
