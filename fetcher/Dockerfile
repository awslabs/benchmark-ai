FROM continuumio/miniconda3

WORKDIR /data/fetcher

COPY ./ /data/fetcher/

RUN conda env create -f environment.yml

ENTRYPOINT [ "/bin/bash", "-c" ]

RUN [ "/bin/bash", "-c", "source activate fetcher && python3 setup.py install" ]

CMD [ "source activate fetcher && fetcher_dispatcher" ]