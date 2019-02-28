FROM ubuntu:18.04

# Install miniconda3
# - obtained from: https://github.com/ContinuumIO/docker-images/blob/master/miniconda3/Dockerfile
RUN apt-get update --fix-missing && \
    apt-get install -y wget bzip2 ca-certificates curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# So that I can use `source` to have conda available in the shell: https://stackoverflow.com/questions/20635472/using-the-run-instruction-in-a-dockerfile-with-source-does-not-work
SHELL ["/bin/bash", "-c"]

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -tipsy && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

RUN /opt/conda/bin/conda config --add channels conda-forge && \
    /opt/conda/bin/conda update -y -n base conda

RUN /opt/conda/bin/conda init bash

# Create a conda environment to run the sidecar
COPY ./environment.yml /tmp/benchmarkai-sidecar-environment.yml
RUN /opt/conda/bin/conda env create -n bai-sidecar -f /tmp/benchmarkai-sidecar-environment.yml

# Get the sidecar contents into the image
RUN mkdir /home/sidecar
WORKDIR /home/sidecar/
COPY . /home/sidecar

CMD ["/opt/conda/bin/conda", "run", "-vvv", "-n", "bai-sidecar", "/home/sidecar/src/main.py"]