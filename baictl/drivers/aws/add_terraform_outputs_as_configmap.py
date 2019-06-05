"""
A script that creates a configmap with all values from `terraform output`.

It skips output values that are marked as "sensitive"
"""
import sys
import tempfile

from ruamel import yaml
from typing import Dict

from argparse import ArgumentParser
import subprocess
import json


def get_terraform_outputs():
    print("Getting terraform outputs")
    outputs = subprocess.check_output("terraform output -json", shell=True)
    outputs = json.loads(outputs.decode())
    return outputs


def filter_terraform_outputs(terraform_outputs: Dict):
    d = {}
    for key, item in terraform_outputs.items():
        if item["sensitive"]:
            print(f"Skipping {key} because it is a sensitive output")
            continue

        if item["type"] == "list":
            value = ",".join(item["value"])
        else:
            value = item["value"]
        d[key] = value
    return d


def kubectl_apply(contents):
    with tempfile.NamedTemporaryFile(prefix="kubectl-apply", mode="w+") as f:
        print("##### Will apply this:")
        print(contents)
        f.write(contents)
        f.flush()
        output = subprocess.check_output("kubectl apply -f {}".format(f.name), shell=True)
        return output.decode()


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("configmap-name")
    args = parser.parse_args(args)
    configmap_name = getattr(args, "configmap-name")

    outputs = get_terraform_outputs()
    values = filter_terraform_outputs(outputs)

    configmap = {"apiVersion": "v1", "data": values, "kind": "ConfigMap", "metadata": {"name": configmap_name}}
    configmap_string = yaml.dump(configmap, Dumper=yaml.RoundTripDumper)
    print(kubectl_apply(configmap_string))
    return 0


if __name__ == "__main__":
    sys.exit(main())
