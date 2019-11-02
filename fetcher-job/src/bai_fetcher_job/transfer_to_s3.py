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
import logging
import tempfile

from bai_io_utils.failures import InvalidDigestError
from bai_io_utils.md5sum import DigestPair, calculate_md5_and_etag
from bai_io_utils.s3_utils import S3Object, check_s3_for_md5, check_s3_for_etag, upload_to_s3, update_s3_hash_tagging
from typing import Optional, TextIO, Callable


logger = logging.getLogger(__name__)

DownloadCallback = Callable[[TextIO, str], None]


def transfer_to_s3(
    download: DownloadCallback, src: str, dst: str, md5: Optional[str] = None, temp_dir: Optional[str] = None
):
    logger.info(f"transfer to s3: {src} -> {dst}")

    s3dst = S3Object.parse(dst)

    logger.info(f"S3dst {s3dst}")

    if md5 and check_s3_for_md5(s3dst, md5):
        logger.info(f"S3 Object with md5 {md5} found - good enough")
        return

    with tempfile.TemporaryFile("r+b", dir=temp_dir) as fp:
        download(fp, src)

        hash_pair: DigestPair = calculate_md5_and_etag(fp)

        if md5:
            if hash_pair.md5 != md5:
                logger.info(f"Invalid md5 {hash_pair.md5} found")
                raise InvalidDigestError()
            logger.info("Hash validation passed")

        # Now we know the "real" etag - may be we can spare the upload?
        if not check_s3_for_etag(s3dst, hash_pair.s3_etag):
            upload_to_s3(fp, s3dst)
        else:
            logger.info(f"S3 Object with etag {hash_pair.s3_etag} found - good enough")

        # If we are here - hash is either missing or wrong.
        # So let's update it
        update_s3_hash_tagging(s3dst, hash_pair.md5)
