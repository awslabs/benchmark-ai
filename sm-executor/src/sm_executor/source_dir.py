#  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import os
import tarfile
import tempfile

from bai_kafka_utils.executors.descriptor import BenchmarkDescriptor
from typing import TextIO, List
from urllib.parse import urlparse

import boto3
from bai_kafka_utils.events import FileSystemObject


class ScriptSourceDirectory:
    SHELL_SHEBANG = "#!/usr/bin/env bash"

    SHELL_ENTRY_POINT = "tmp_entry.sh"

    PYTHON_ENTRY_POINT = "tmp_entry.py"

    @staticmethod
    def create(descriptor: BenchmarkDescriptor, dst_path: str, scripts: List[FileSystemObject] = None, s3=None):
        with open(os.path.join(dst_path, ScriptSourceDirectory.SHELL_ENTRY_POINT), "wt") as bash_entry:
            ScriptSourceDirectory._create_shell_entrypoint(bash_entry, descriptor)

        with open(os.path.join(dst_path, ScriptSourceDirectory.PYTHON_ENTRY_POINT), "wt") as py_bash_wrapper:
            ScriptSourceDirectory._create_python_shell_wrapper(py_bash_wrapper)

        if scripts:
            s3 = s3 or boto3.client("s3")

            for file_obj in scripts:
                ScriptSourceDirectory._download_script(file_obj, dst_path, s3)

    @staticmethod
    def _download_script(file_obj: FileSystemObject, dst_path: str, s3client):
        parsed_uri = urlparse(file_obj.dst)
        file = parsed_uri.path[1:]
        bucket = parsed_uri.netloc
        with tempfile.TemporaryFile("r+b") as f:
            s3client.download_fileobj(bucket, file, f)
            f.seek(0)
            tar = tarfile.open(fileobj=f)
            tar.extractall(path=dst_path)
            tar.close()

    @staticmethod
    def _create_shell_entrypoint(file: TextIO, descriptor: BenchmarkDescriptor):
        file.write(ScriptSourceDirectory.SHELL_SHEBANG + os.linesep)
        for var, val in descriptor.env.vars.items():
            file.write(f'export {var}="{val}"' + os.linesep)
        file.write(descriptor.ml.benchmark_code + os.linesep)

    @staticmethod
    def _create_python_shell_wrapper(file: TextIO):
        file.write("import os" + os.linesep)
        file.write("myCmd = 'chmod 777 tmp_entry.sh && ./tmp_entry.sh'" + os.linesep)
        file.write("os.system(myCmd)" + os.linesep)
