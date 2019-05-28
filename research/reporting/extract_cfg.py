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
  report_cfg = {}
  benchmark_count = 0
  report_type = ''
  benchmarks = []
  with open(report_table_csv, mode='r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)

    for benchmark in reader:
      report_type = benchmark[0]
      labels = {}
      metrics = {}
      index = 1
      benchmark_count = benchmark_count + 1
      for index in range(0, len(benchmark)):
        value = benchmark[index]
        
        if not value:
          continue

        if is_number(value):
          metrics[header[index]] = float(value)
        else:
          labels[header[index]] = value

      benchmarks.append({
        'name': '{}_benchmark_{}'.format(report_type.replace(' ', ''), benchmark_count),
        'labels': labels,
        'metrics': metrics
        })
  return benchmarks

def main():
  report_tables = glob('./*.csv')
  benchmarks = []
  for report_table in report_tables:
    benchmarks.extend(get_benchmarks(report_table))

  cfg = {
    'benchmarks': benchmarks
  }
  with open('report_cfg.yaml', 'w') as yaml_file:
    yaml.dump(cfg, yaml_file, default_flow_style=False)


if __name__ == '__main__':
  main()