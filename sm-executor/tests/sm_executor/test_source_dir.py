import os
import tarfile

import boto3
from bai_kafka_utils.events import FileSystemObject
from bai_kafka_utils.executors.descriptor import BenchmarkDescriptor
from botocore.stub import Stubber
from io import BytesIO, StringIO, IOBase
from pytest import fixture
from typing import NamedTuple, List, Callable
from unittest.mock import call

from sm_executor import source_dir
from sm_executor.source_dir import ScriptSourceDirectory

EXCHANGE_BUCKET = "some_bucket"

SECOND_KEY = "other.tar"
FIRST_KEY = "one.tar"

FIRST_FILE_NAME = "one.py"
SECOND_FILE_NAME = "other.py"

SECOND_SCRIPT_TAR = f"s3://{EXCHANGE_BUCKET}/{SECOND_KEY}"

FIRST_SCRIPT_TAR = f"s3://{EXCHANGE_BUCKET}/{FIRST_KEY}"

FIRST_CONTENT = b"HUGE FILE"
SECOND_CONTENT = b"OTHER HUGE FILE"

DST_PATH = "/tmp/mysrc-dir"

SCRIPTS = [FileSystemObject(FIRST_SCRIPT_TAR), FileSystemObject(SECOND_SCRIPT_TAR)]

PatchedOpen = NamedTuple("y", fields=[("open", Callable[[str, str], IOBase]), ("files", List[IOBase])])


def uncloseable(file: IOBase):
    # Break the close method call - so we can inspect the contents of memory file
    def _close():
        pass

    file.close = _close
    return file


@fixture
def mock_open(mocker) -> PatchedOpen:
    files = [uncloseable(StringIO()), uncloseable(StringIO()), uncloseable(BytesIO()), uncloseable(BytesIO())]
    mock_open = mocker.patch.object(source_dir, "open", side_effect=files)
    return PatchedOpen(open=mock_open, files=files)


@fixture
def mock_bltn_open(mocker) -> PatchedOpen:
    files = [uncloseable(BytesIO()), uncloseable(BytesIO())]
    mock_open = mocker.patch.object(tarfile, "bltn_open", side_effect=files)
    return PatchedOpen(open=mock_open, files=files)


def mock_file(stub, key, name, content):
    len_of_content = len(content)
    stub.add_response(method="head_object", service_response={"ContentLength": len_of_content})

    content_stream = BytesIO(content)
    tar_stream = BytesIO()

    tar = tarfile.open(fileobj=tar_stream, mode="w", name=key)
    tarinfo = tarfile.TarInfo(name)
    tarinfo.size = len_of_content
    tar.addfile(tarinfo, fileobj=content_stream)
    tar.close()

    tar_stream.seek(0)
    stub.add_response(method="get_object", service_response={"Body": tar_stream})


MOCKED_REGION = "us-east-1"


@fixture
def mock_s3():
    s3client = boto3.client("s3", region_name=MOCKED_REGION)
    stub = Stubber(s3client)

    mock_file(stub, FIRST_KEY, FIRST_FILE_NAME, FIRST_CONTENT)
    mock_file(stub, SECOND_KEY, SECOND_FILE_NAME, SECOND_CONTENT)

    stub.activate()
    return s3client


def validate_unpacked_script(file: BytesIO, content):
    assert file.getvalue() == content


def test_create_dir_download_files(
    descriptor: BenchmarkDescriptor, mock_open: PatchedOpen, mock_bltn_open: PatchedOpen, mock_s3
):
    ScriptSourceDirectory.create(descriptor, DST_PATH, SCRIPTS, mock_s3)

    assert mock_bltn_open.open.call_args_list == [
        call(DST_PATH + "/" + FIRST_FILE_NAME, "wb"),
        call(DST_PATH + "/" + SECOND_FILE_NAME, "wb"),
    ]

    validate_unpacked_script(mock_bltn_open.files[0], FIRST_CONTENT)
    validate_unpacked_script(mock_bltn_open.files[1], SECOND_CONTENT)


def test_create_dir_shell_entry_point(descriptor: BenchmarkDescriptor, mock_open: PatchedOpen):
    descriptor.env.vars = {"FOO": "BAR"}

    ScriptSourceDirectory.create(descriptor, DST_PATH)

    assert call(os.path.join(DST_PATH, ScriptSourceDirectory.SHELL_ENTRY_POINT), "wt") in mock_open.open.call_args_list

    shell_entry = mock_open.files[0]
    lines = [line for line in shell_entry.getvalue().split(os.linesep) if line]

    assert lines == [ScriptSourceDirectory.SHELL_SHEBANG, 'export FOO="BAR"', descriptor.ml.benchmark_code]
