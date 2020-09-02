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
from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json

from bai_kafka_utils.events import FetcherStatus, FetchedType, DownloadableContent

DEFAULT_ENCODING = "utf-8"


@dataclass
@dataclass_json
class FetcherResult:
    status: FetcherStatus
    type: Optional[FetchedType] = None
    message: Optional[str] = None

    def to_binary(self):
        return self.to_json().encode(DEFAULT_ENCODING)

    @classmethod
    def from_binary(cls, bin_data):
        return FetcherResult.from_json(bin_data.decode(DEFAULT_ENCODING))

    def update(self, data_set: DownloadableContent):
        data_set.status = self.status
        data_set.type = self.type

        if not self.status.success:
            data_set.message = self.message
            data_set.dst = None
