#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup

from os.path import join, abspath, dirname

here = abspath(dirname(__file__))
bai_project_path = abspath(join(here, ".."))

setup(
    name='fetcher_dispatcher',
    url='https://github.com/MXNetEdge/benchmark-ai',
    package_dir={'': 'src'},
    packages=find_packages("src") + [join(bai_project_path, "kafka-utils/src")],
    include_package_data=True,
    entry_points={
        "console_scripts": ["fetcher_dispatcher=fetcher_dispatcher.__main__:main"]
    }
)
