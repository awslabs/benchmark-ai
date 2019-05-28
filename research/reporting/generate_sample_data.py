import json
import pytz
import time
import random
import yaml
from elasticsearch import Elasticsearch
from functools import partial
from datetime import datetime, timedelta

es_index = 'dummy-metrics'
doc_type = 'metric'


class DummyBenchmark:

  def __init__(self, id, labels={}):
    self._id = id
    self._metrics = {}
    self._labels = {
      'benchmark_id': id,
      **labels 
    }

  def add_metric(self, name, generator_fn):
    if name not in self._metrics:
      self._metrics[name] = generator_fn

  def add_label(self, name, value):
    if name not in self._labels.values():
      self._labels[name] = value

  def log(self, timestamp):
    log_line = {str(key): generate() for key, generate in self._metrics.items()}
    log_line.update(self._labels)
    log_line['@timestamp'] = timestamp.isoformat()
    return log_line

  def has_metrics(self):
    return len(self._metrics) > 0


def normal(mu, sigma):
  return partial(random.gauss, mu, sigma)


def now():
  # must have timezone info for ES to pick it up
  return pytz.utc.localize(datetime.utcnow()) 


def generate_logs(es, benchmark, start):
  timestamp = start
  present = now()
  while timestamp < present:
    log_line = benchmark.log(timestamp)
    print(log_line)
    log_id = hash(frozenset(log_line.items()))
    print(es.index(index=es_index, doc_type=doc_type, id=log_id, body=log_line))
    timestamp = timestamp + timedelta(seconds=30)


def get_benchmarks(cfg_yaml):
  benchmarks = []
  with open(cfg_yaml) as cfg_file:
      cfg = yaml.safe_load(cfg_file)
      for benchmark in cfg['benchmarks']:
        dummy = DummyBenchmark(benchmark['name'], benchmark['labels'])
        for name, mean in benchmark['metrics'].items():
          dummy.add_metric(name, normal(mean, 0.05*mean))
        benchmarks.append(dummy)
  return benchmarks


def main():
  es = Elasticsearch(['localhost:9200'])

  # ignore 400 error (index already exists)
  es.indices.create(index=es_index, ignore=400)
  
  benchmarks = get_benchmarks('report_cfg.yaml')

  for benchmark in benchmarks:
    if benchmark.has_metrics():
      generate_logs(es, benchmark, now() - timedelta(hours=1))


if __name__ == '__main__':
  main()
