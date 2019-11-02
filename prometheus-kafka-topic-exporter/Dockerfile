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
FROM openjdk:12.0.1-jdk-oraclelinux7

# exporter.port=12340 in kafka-topic-exporter.properties.template
EXPOSE 12340

RUN yum install -y wget
RUN wget -O /opt/kafka-topic-exporter.jar https://github.com/ogibayashi/kafka-topic-exporter/releases/download/v0.0.6/kafka-topic-exporter-0.0.6-jar-with-dependencies.jar
RUN wget -O /tmp/kafka_binary.tgz http://ftp-stud.hs-esslingen.de/pub/Mirrors/ftp.apache.org/dist/kafka/2.3.0/kafka_2.12-2.3.0.tgz && \
    mkdir /opt/kafka && \
    tar -xzf /tmp/kafka_binary.tgz --strip 1 -C /opt/kafka && \
    rm /tmp/kafka_binary.tgz

ADD run.sh /opt/run.sh

# Config has to be mounted at /config
ENTRYPOINT [ "/bin/bash", "-c" ]
CMD [ "/opt/run.sh" ]