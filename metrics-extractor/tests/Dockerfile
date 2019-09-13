FROM python:3-alpine

RUN mkdir -p /home/benchmark
COPY test.py /home/benchmark
WORKDIR /home/benchmark/

CMD ["python3", "test.py"]
