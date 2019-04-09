FROM mxnet/python:1.4.0_gpu_cu100_py3

RUN apt-get install unzip
RUN pip install benchmarkai-client-lib
RUN mkdir /home/benchmark
COPY src/ /home/benchmark
WORKDIR /home/benchmark/
