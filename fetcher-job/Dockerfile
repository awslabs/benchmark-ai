FROM continuumio/miniconda3 as base

WORKDIR /data/fetcher-job

#Stable files
COPY environment.yml /data/fetcher-job/

RUN conda env create -f environment.yml -p /opt/fetcher-job

COPY . /data/fetcher-job
RUN /opt/fetcher-job/bin/python setup.py install

########################################
# Build the final image
########################################
FROM ubuntu:18.04

COPY --from=base /opt/fetcher-job /opt/fetcher-job

# A workdir only for convenience
WORKDIR /opt/fetcher-job/bin

ENTRYPOINT ["/opt/fetcher-job/bin/bai-fetcher-job"]
