#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup


def findall(root_directory):
    import os

    exclude_prefixes = ("__", ".")  # exclusion prefixes
    for dirpath, dirnames, filenames in os.walk(root_directory):
        # exclude all dirs starting with exclude_prefixes
        dirnames[:] = [dirname for dirname in dirnames if not dirname.startswith(exclude_prefixes)]
        for filename in filenames:
            yield os.path.join(dirpath, filename)


bash_baictl_files = [p[len("src/baictl/") :] for p in findall("src/baictl/bash")]

setup(
    name="baictl",
    url="https://github.com/MXNetEdge/benchmark-ai",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"baictl": bash_baictl_files},
    include_package_data=True,
    entry_points={"console_scripts": ["baictl=baictl.__main__:main"]},
)
