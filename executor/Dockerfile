FROM continuumio/miniconda3

WORKDIR /data/executor

#Infrequent changes
COPY environment.yml setup.py /data/executor/

RUN conda env create -f environment.yml -p /opt/executor

#Very frequent changes
COPY src /data/executor/src

RUN [ "/opt/executor/bin/python3", "setup.py", "install" ]

ENTRYPOINT [ "/opt/executor/bin/executor" ]