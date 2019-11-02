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

from retrying import retry

from bai_io_utils.failures import RetryableError
from bai_kafka_utils.events import ContentSizeInfo
from preflight.http_estimator import http_estimate_size
from preflight.s3_estimator import s3_estimate_size

MAX_ATTEMPTS = 3

WAIT_EXPONENTIAL_MAX_MS = 3000

WAIT_EXPONENTIAL_MULTIPLIER_MS = 500


class UnknownSchemeException(Exception):
    pass


@retry(
    retry_on_exception=lambda exc: isinstance(exc, RetryableError),
    wait_exponential_multiplier=WAIT_EXPONENTIAL_MULTIPLIER_MS,
    wait_exponential_max=WAIT_EXPONENTIAL_MAX_MS,
    stop_max_attempt_number=MAX_ATTEMPTS,
)
def estimate_fetch_size(src: str) -> ContentSizeInfo:
    parsed = urlparse(src)
    if parsed.scheme == "http" or parsed.scheme == "https":
        return http_estimate_size(src)
    if parsed.scheme == "s3":
        return s3_estimate_size(src)
    raise UnknownSchemeException(f"Unknown scheme '{parsed.scheme}' in '{src}'")
