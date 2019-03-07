FROM python:3-alpine

RUN pip3 install benchmarkai-client-lib
RUN mkdir /home/benchmark
COPY src/ /home/benchmark
WORKDIR /home/benchmark/

CMD ["python3", "hello-world.py"]
