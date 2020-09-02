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

from bai_io_utils.http_utils import http_download
from typing import Optional


from bai_fetcher_job.transfer_to_s3 import transfer_to_s3

logger = logging.getLogger(__name__)


def http_to_s3(src: str, dst: str, md5: Optional[str] = None, temp_dir: Optional[str] = None):
    transfer_to_s3(http_download, src, dst, md5, temp_dir)
