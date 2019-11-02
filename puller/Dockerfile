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
FROM       alpine:3.3

WORKDIR "/data"

RUN apk update && \
    apk add \
      libarchive-tools \
      bash \
      'python<3.0' \
      'py-pip<8.2' \
    && \
    rm -rf /var/cache/apk/*

RUN pip install awscli
# Replace busybox mini-tar with a smarter bsdtar+libarchive
RUN mv /bin/tar /bin/oldtar && ln -s $(which bsdtar) /bin/tar

COPY download-s3-files /opt/puller/download-s3-files

ENTRYPOINT ["/bin/bash", "/opt/puller/download-s3-files"]
CMD []
