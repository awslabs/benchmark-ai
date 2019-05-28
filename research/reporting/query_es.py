import pytz
import time
import yaml
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

es_index = 'dummy-metrics'
doc_type = 'metric'

def create_agg_query(benchmark_type, metrics, from_time):
  source = ["benchmark_id"]
  source.extend(metrics)
  query = {
    "_source": source,
    "query": {
      "bool": {
        "must": [{
          "match": {
            "Type": benchmark_type
          }
        }],
        "filter": {
          "range": {
            "@timestamp": {
              "gte": from_time.isoformat()
            }
          }
        }
      }
    },
    "size": 0,  # don't return individual rows
    "aggs": {
      "benchmarck_aggs": {
        "aggs": {}, # to be populated
        "terms": {
          "field": "benchmark_id.keyword",
          "size": 100 # don't know how to page results yet... should be >= of benchmarks in type
        }
      }
    }
  }

  for metric_name in metrics:
    query['aggs']['benchmarck_aggs']['aggs'].update({
      metric_name: {
        "avg": {
          "field": metric_name
        }
      }
    })

  return query

def load_report_cfg(report_cfg_yaml):
  with open(report_cfg_yaml, mode="r", encoding="utf-8-sig") as cfg_file:
    return yaml.safe_load(cfg_file)

def get_benchmark_types(report_cfg):
  return set([benchmark['labels']['Type'] for benchmark in report_cfg['benchmarks']])

def get_benchmark_metrics(report_cfg, benchmark_type):
  benchmarks = [benchmark for benchmark in report_cfg['benchmarks'] if benchmark['labels']['Type'] == benchmark_type]
  metrics = set()
  for benchmark in benchmarks:
    metrics.update(benchmark['metrics'].keys())
  return metrics

def get_benchmark_labels(report_cfg, benchmark_type):
  benchmarks = [benchmark for benchmark in report_cfg['benchmarks'] if benchmark['labels']['Type'] == benchmark_type]
  metrics = set()
  for benchmark in benchmarks:
    metrics.update(benchmark['labels'].keys())
  return metrics

def get_benchmarks_for_type(report_cfg, benchmark_type):
  return [benchmark for benchmark in report_cfg['benchmarks'] if benchmark['labels']['Type'] == benchmark_type]

def get_aggregates(es, benchmark_type, metrics, from_time):
  query = create_agg_query(benchmark_type, metrics, from_time)
  res = es.search(index=es_index, body=query)
  aggregates = res['aggregations']['benchmarck_aggs']['buckets']
  results = {}
  for agg in aggregates:
    r = {}
    for metric in metrics:
      r[metric] = agg[metric]['value']
    results[agg['key']] = r
  return results

def main():
  es = Elasticsearch(["localhost:9200"])

  current_time = pytz.utc.localize(datetime.utcnow())
  from_time = current_time - timedelta(weeks=1)

  report_cfg = load_report_cfg('report_cfg.yaml')
  benchmark_types = get_benchmark_types(report_cfg)
  # print(benchmark_types)
  metrics = get_benchmark_metrics(report_cfg, 'Training CV')
  # print(metrics)
  
  aggregate_metrics = get_aggregates(es, 'Training CV', metrics, from_time)
  benchmarks = get_benchmarks_for_type(report_cfg, 'Training CV')
  # labels = get_benchmark_labels(report_cfg, 'Training CV')
  labels = ["Type","Framework","Framework Desc","Model","Precision","Benchmark Desc","Instance Type","Top 1 Val Acc","Top 1 Train Acc","Throughput (/s)","Time to Train (s)","CPU Memory (mb)","GPU Memory Max (mb)","GPU Memory Mean (mb)","Uptime (s)"]
  header = [*labels, *metrics]
  print(','.join(header))
  for benchmark in benchmarks:
    benchmark_id = benchmark['name']
    out = {**benchmark['labels']}
    if benchmark_id in aggregate_metrics:
      out.update(aggregate_metrics[benchmark_id])
    row = []
    for key in header:
      if key in out:
        row.append(str(out[key]))
      else:
        row.append('')
    print(','.join(row))
  

  

if __name__ == '__main__':
  main()