#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from os.path import join, abspath, dirname

from setuptools import find_packages, setup

here = abspath(dirname(__file__))
bai_project_path = abspath(join(here, os.pardir))

setup(
    description=".",
    name="bai_client",
    url="https://github.com/awslabs/benchmark-ai",
    requires=["bai_kafka_utils"],
    package_dir={"": "src"},
    packages=find_packages("src"),
)
