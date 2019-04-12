FROM continuumio/miniconda3

WORKDIR /data/fetcher-job

#Stable files
COPY environment.yml /data/fetcher-job/

RUN conda env create -f environment.yml -p /opt/fetcher-job

#Source to be changed frequently
COPY fetcher.py /data/fetcher-job/

ENTRYPOINT [ "/opt/fetcher-job/bin/python3", "fetcher.py" ]

