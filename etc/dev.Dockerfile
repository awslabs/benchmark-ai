### Development Dockerfile for all projects
# Example:
# cd executor
# docker build -f etc/dev.Dockerfile -t anubis:base
# docker run -it anubis:base make

FROM continuumio/miniconda3:4.6.14

RUN conda install --override-channels --channel defaults --name base --yes conda==4.6.14

#MAKE
RUN apt-get update

RUN apt-get install -y --no-install-recommends \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg2 \
  software-properties-common \
  make \
  openjdk-8-jdk

# Clojure
RUN curl -L https://download.clojure.org/install/linux-install-1.10.1.469.sh -o /tmp/clojure-install.sh && \
  chmod +x /tmp/clojure-install.sh && \
  /tmp/clojure-install.sh

# Lein and dependencies
RUN curl -L https://raw.githubusercontent.com/technomancy/leiningen/stable/bin/lein -o /usr/local/bin/lein && \
  chmod a+x /usr/local/bin/lein && \
  /usr/local/bin/lein

RUN lein

#DOCKER for integration tests
ARG DOCKER_CHANNEL=stable
# We pin this version due to (unfortunate) incompatibility of the later versions
# See here: https://github.com/docker/for-linux/issues/219
# Need to dive deeper
ARG DOCKER_VERSION=17.09.1

RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
RUN add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/debian \
  $(lsb_release -cs) \
  ${DOCKER_CHANNEL}"
RUN apt-get update && apt-get install -y --no-install-recommends docker-ce=${DOCKER_VERSION}~ce-0~debian && \
  docker -v && \
  dockerd -v

COPY ci/start-dind.sh /usr/local/bin/start-dind.sh
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
