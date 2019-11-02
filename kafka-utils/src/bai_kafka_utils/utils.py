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
import encodings
import hashlib
import platform
import random
import string
import time
import uuid

DEFAULT_ENCODING = encodings.utf_8.getregentry().name
METRICS_PUSHER_BACKEND_ARG_PREFIX = "backend_arg_"
METRICS_PUSHER_CUSTOM_LABEL_PREFIX = "custom_label_"


def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def md5sum(str_to_hash: str, encoding: str = DEFAULT_ENCODING):
    md5hash = hashlib.md5()
    md5hash.update(str_to_hash.encode(encoding))
    return md5hash.hexdigest()


def generate_uuid():
    return str(uuid.uuid4())


def now_milliseconds():
    """
    :return: current time in milliseconds
    """
    return int(time.time() * 1000)


def get_pod_name():
    return platform.node()
