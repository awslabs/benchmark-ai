FROM continuumio/miniconda3

WORKDIR /data/fetcher-job

COPY environment.yml /data/fetcher-job/
COPY fetcher.py /data/fetcher-job/

RUN conda env create -f environment.yml

ENTRYPOINT [ "/opt/conda/envs/fetcher-job/bin/python3", "fetcher.py" ]

