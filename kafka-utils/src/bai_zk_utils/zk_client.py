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
from kazoo.client import KazooClient

from bai_zk_utils.states import FetcherResult


def update_zk_node(zk_node_path: str, zookeeper_ensemble: str, state: FetcherResult):
    zk = KazooClient(hosts=zookeeper_ensemble)
    zk.start()
    zk.set(zk_node_path, state.to_binary())
    zk.stop()
