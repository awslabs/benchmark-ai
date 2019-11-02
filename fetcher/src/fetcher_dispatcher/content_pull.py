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
from urllib.parse import urlparse

from bai_kafka_utils.events import DownloadableContent
from bai_kafka_utils.utils import md5sum


def get_content_dst(content: DownloadableContent, s3_bucket: str):
    # Req 1 - same content with different hashes should get different dest
    # Req 2 - at least some grade of human readability
    s3uri = f"s3://{s3_bucket}/data_sets/{md5sum(content.src)}"

    if content.md5:
        s3uri += f"/{content.md5}"

    parsed = urlparse(content.src)
    if parsed.path:
        s3uri += parsed.path

    return s3uri
