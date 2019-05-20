import hashlib

from typing import TextIO, NamedTuple

S3_MAX_CHUNK_BYTES = 8 * 1024 * 1024  # 8 MB

DigestPair = NamedTuple("DigestPair", [("md5", str), ("s3_etag", str)])


# Calculates MD5 and ETag in a single run.
# Hash state for ETag is created lazily, just for the files > 8Mb
def calculate_md5_and_etag(fp: TextIO, chunk_size=S3_MAX_CHUNK_BYTES) -> DigestPair:
    fp.seek(0)

    global_hash = hashlib.md5()
    md5s = []
    first = True
    for data in iter(lambda: fp.read(chunk_size), b""):
        global_hash.update(data)
        if first:
            first = False
            md5s.append(global_hash.digest())
        else:
            current_chunks_hash = hashlib.md5(data)
            md5s.append(current_chunks_hash.digest())
    joining_etag_hash = hashlib.md5(b"".join(md5s))

    global_md5 = global_hash.hexdigest()

    return DigestPair(
        s3_etag="{}-{}".format(joining_etag_hash.hexdigest(), len(md5s)) if len(md5s) > 1 else global_md5,
        md5=global_md5,
    )
