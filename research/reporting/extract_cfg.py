import csv
import yaml
from glob import glob

def is_number(value):
  try:
    float(value)
    return True
  except ValueError:
    return False


def get_benchmarks(report_table_csv):
  
  benchmark_type = ''
  benchmarks = []

  with open(report_table_csv, mode='r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)

    for benchmark_number, benchmark in enumerate(reader):
      benchmark_type = benchmark[0]
      benchmark_id = '{}_benchmark_{}'.format(benchmark_type.replace(' ', ''), benchmark_number)
      labels = {}
      metrics = {}

      for index, value in enumerate(benchmark):        
        if not value:
          continue

        if is_number(value):
          metrics[header[index]] = float(value)
        else:
          labels[header[index]] = value

      benchmarks.append({
        'benchmark_id': benchmark_id,
        'labels': labels,
        'metrics': metrics
        })

  return {
    benchmark_type: benchmarks
  }

def main():
  report_tables = glob('./*.csv')
  benchmarks = {}
  for report_table in report_tables:
    benchmarks.update(get_benchmarks(report_table))

  with open('report_cfg.yaml', 'w') as yaml_file:
    yaml.dump(benchmarks, yaml_file, default_flow_style=False)


if __name__ == '__main__':
  main()