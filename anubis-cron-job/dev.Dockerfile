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
FROM continuumio/miniconda3:4.6.14

RUN conda install --override-channels --channel defaults --name base --yes conda==4.6.14

#MAKE
RUN apt-get update && apt-get install make

#DOCKER for integration tests
ARG DOCKER_CHANNEL=stable
# We pin this version due to (unfortunate) incompatibility of the later versions
# See here: https://github.com/docker/for-linux/issues/219
# Need to dive deeper
ARG DOCKER_VERSION=17.09.1

RUN apt-get install -y --no-install-recommends \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg2 \
  software-properties-common
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/debian \
   $(lsb_release -cs) \
   ${DOCKER_CHANNEL}"
RUN apt-get update && apt-get install -y --no-install-recommends docker-ce=${DOCKER_VERSION}~ce-0~debian && \
  docker -v && \
  dockerd -v

COPY start-dind.sh /usr/local/bin/start-dind.sh
RUN chmod +x /usr/local/bin/start-dind.sh

VOLUME /var/lib/docker

#kubeadm local CLUSTER 
RUN curl -L https://github.com/kubernetes-sigs/kind/releases/download/v0.3.0/kind-linux-amd64 -o /usr/local/bin/kind && \
    chmod +x /usr/local/bin/kind

#kubectl version 1.14 to have native kustomize
RUN apt-get install -y apt-transport-https
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y kubectl=1.14.*

ENV K8S_KINDEST_V12 kindest/node:v1.12.8@sha256:cc6e1a928a85c14b52e32ea97a198393fb68097f14c4d4c454a8a3bc1d8d486c
