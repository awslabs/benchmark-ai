#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="executor",
    url="https://github.com/MXNetEdge/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"executor": "*.yaml", "transpiler.templates": "*.yaml"},
    entry_points={"console_scripts": ["start=executor.__main__:main"]},
)
