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
from botocore.exceptions import ClientError


def get_client_error_message(client_error: ClientError, default: str = None):
    return client_error.response.get("Error", {}).get("Message", default)


def is_not_found_error(client_error: ClientError):
    error_message = get_client_error_message(client_error, default="")
    return error_message.lower().find("not found") > 0
