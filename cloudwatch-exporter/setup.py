#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from os.path import join, abspath, dirname

from setuptools import find_packages, setup

here = abspath(dirname(__file__))
bai_project_path = abspath(join(here, os.pardir))
setup(
    name="cloudwatch_exporter",
    url="https://github.com/awslabs/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"console_scripts": ["start=cloudwatch_exporter.__main__:main"]},
)
