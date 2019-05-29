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

def get_aggregates(es, benchmark_type, metrics, from_time):
  query = create_agg_query(benchmark_type, metrics, from_time)
  res = es.search(index=es_index, body=query)
  aggregates = res['aggregations']['benchmarck_aggs']['buckets']
  results = {}
  for aggregate in aggregates:
    benchmark_id = aggregate['key']
    metric_values = {}
    for metric in metrics:
      metric_values[metric] = aggregate[metric]['value']
    results[benchmark_id] = metric_values
  return results


def print_report(es, benchmark_type, benchmark_cfg, from_time):
  metrics = set()
  labels = set()

  # collect the set of unique metrics and labels
  # across all benchmarks for the report
  for benchmark in benchmark_cfg:
    metrics.update(benchmark['metrics'].keys())
    labels.update(benchmark['labels'].keys())

  aggregates = get_aggregates(es, benchmark_type, metrics, from_time)

  header = [*labels, *metrics]

  print(','.join(header))
  for benchmark in benchmark_cfg:
    benchmark_id = benchmark['benchmark_id']
    row_obj = { **benchmark['labels'] }
    if benchmark_id in aggregates:
      row_obj.update(**aggregates[benchmark_id])
    row = [str(row_obj[key]) if key in row_obj else '' for key in header]
    print(','.join(row))


def main():
  es = Elasticsearch(["localhost:9200"])

  current_time = pytz.utc.localize(datetime.utcnow())
  from_time = current_time - timedelta(weeks=1)

  report_cfg = load_report_cfg('report_cfg.yaml')
  
  for benchmark_type, benchmark_cfg in report_cfg.items():
    print_report(es, benchmark_type, benchmark_cfg, from_time)
    print()


if __name__ == '__main__':
  main()
