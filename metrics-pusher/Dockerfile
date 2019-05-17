FROM continuumio/miniconda3 as base

RUN conda update -n base -c conda-forge conda

######################
# Infrequent changes #
######################
# Create a conda environment to run the metrics-pusher
COPY ./environment.yml /tmp/benchmarkai-metrics-pusher-environment.yml
RUN conda env create -f /tmp/benchmarkai-metrics-pusher-environment.yml -p /opt/metrics-pusher

####################
# Frequent changes #
####################

# Get the metrics-pusher contents into the image
RUN mkdir /home/metrics-pusher
COPY . /home/metrics-pusher
WORKDIR /home/metrics-pusher
RUN /opt/metrics-pusher/bin/python setup.py install

########################################
# Build the final image
########################################
FROM ubuntu:18.04

COPY --from=base /opt/metrics-pusher /opt/metrics-pusher

# A workdir only for convenience
WORKDIR /opt/metrics-pusher/bin

ENTRYPOINT ["/opt/metrics-pusher/bin/bai-metrics-pusher"]
