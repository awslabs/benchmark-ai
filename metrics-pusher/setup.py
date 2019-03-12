#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

setup(
    name='benchmarkai-metrics-pusher',
    url='https://github.com/MXNetEdge/benchmark-ai',
    package_dir={'': 'src'},
    packages=find_packages("src"),
    include_package_data=True,
    entry_points={
        "console_scripts": ["benchmarkai_metrics_pusher = benchmarkai_metrics_pusher.__main__:main"]
    }
)
