import pytz
import time
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

es_index = 'new-dummy-metrics-5'
doc_type = 'metric'

def main():
  es = Elasticsearch(['localhost:9200'])

  current_time = pytz.utc.localize(datetime.utcnow())
  from_time = current_time - timedelta(weeks=1)
  print(from_time.isoformat())

  query ={
   "query": {
      "match": {
        "Type": {
          "query": "Inference"
        }
      },
      "filter": {
        "range": {
          "@timestamp": {
            "gte": from_time.isoformat()
          }
        }
      }
    }
  }

  res = es.search(index=es_index, body=query, size="50")
  for hit in res['hits']['hits']:
    print(hit['_source'])

if __name__ == '__main__':
  main()