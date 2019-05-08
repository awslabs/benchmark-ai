import hashlib

from typing import TextIO

from benchmarkai_fetcher_job.failures import InvalidDigestException

BUFFER_SIZE = 4096


def md5sum(fp: TextIO) -> str:
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: fp.read(BUFFER_SIZE), b""):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()


def validate_md5(fp: TextIO, md5: str):
    actual_md5 = md5sum(fp)
    if actual_md5 != md5:
        raise InvalidDigestException()
