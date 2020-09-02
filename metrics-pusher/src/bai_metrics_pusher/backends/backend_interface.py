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
import abc

from typing import List, Union, Dict

AcceptedMetricTypes = Union[float, List[float]]


class Backend(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def emit(self, metrics: Dict[str, AcceptedMetricTypes]):
        """
        Emits the metrics to the backend.
        """
        pass

    @abc.abstractmethod
    def close(self):
        """
        Closes the backend.

        After calling this method, the object is unusable.
        """
        pass
