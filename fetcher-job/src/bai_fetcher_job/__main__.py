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
import os

from bai_fetcher_job.args import FetcherJobConfig, get_fetcher_job_args
from bai_fetcher_job.fetcher import retrying_fetch
from bai_kafka_utils.logging import configure_logging


def main(argv=None):
    cfg: FetcherJobConfig = get_fetcher_job_args(argv, os.environ)
    configure_logging(level=cfg.logging_level)

    retrying_fetch(cfg)


if __name__ == "__main__":
    main()
