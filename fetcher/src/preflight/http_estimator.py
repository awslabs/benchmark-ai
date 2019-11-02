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
import pycurl

from bai_io_utils.http_utils import http_perform
from bai_kafka_utils.events import ContentSizeInfo


def http_estimate_size(src) -> ContentSizeInfo:
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, src)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 60)  # 60s should be enough to send HEAD and get back
    curl.setopt(pycurl.HEADER, 1)
    curl.setopt(pycurl.NOBODY, 1)

    http_perform(curl)

    content_length = curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD)

    return ContentSizeInfo(int(content_length), 1, int(content_length))
