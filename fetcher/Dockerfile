FROM continuumio/miniconda3

WORKDIR /data/fetcher

#Infrequent changes
COPY environment.yml setup.py /data/fetcher/

RUN conda env create -f environment.yml -p /opt/fetcher

#Very frequent changes
COPY src /data/fetcher/src

ENTRYPOINT [ "/bin/bash", "-c" ]

RUN [ "/opt/fetcher/bin/pip", "install", "-r", "requirements.txt" ]
RUN [ "/opt/fetcher/bin/python3", "setup.py", "install" ]

CMD [ "/opt/fetcher/bin/fetcher_dispatcher" ]