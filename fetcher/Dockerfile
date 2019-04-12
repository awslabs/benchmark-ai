FROM continuumio/miniconda3

WORKDIR /data/fetcher

#Infrequent changes
COPY environment.yml setup.py /data/fetcher/

RUN conda env create -f environment.yml

#Very frequent changes
COPY src /data/fetcher/src

ENTRYPOINT [ "/bin/bash", "-c" ]

RUN [ "/bin/bash", "-c", "source activate fetcher && python3 setup.py install" ]

CMD [ "source activate fetcher && fetcher_dispatcher" ]