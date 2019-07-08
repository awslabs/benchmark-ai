#!/usr/bin/env python3
import json
import os

import requests
from pathlib import Path

import shutil
import textwrap
from collections import namedtuple
from time import time

from typing import Dict

import subprocess
import argparse
import boto3


def open_terraform_vars_file(filename) -> Dict[str, str]:
    if not os.path.exists(filename):
        return {}

    d = {}
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            equal_index = line.index("=")
            key = line[:equal_index]
            value = line[equal_index + 1 :]
            d[key.strip()] = value.strip().strip('"')
    return d


class Config:
    VARIABLE_NAMES = {
        "github_branch",
        "github_organization",
        "chime_hook_url",
        "run_integration_tests",
        "region",
        "bucket",
        "prefix_list_id",
    }

    def __init__(self):
        existing_values = {}
        existing_values.update(open_terraform_vars_file(".terraform/ci-backend-config"))
        existing_values.update(open_terraform_vars_file("terraform.tfvars"))

        self.variables = {"region": "us-east-1"}
        for var_name in Config.VARIABLE_NAMES:
            self.variables[var_name] = existing_values.get(var_name, self.variables.get(var_name, None))

    def __getitem__(self, item):
        return self.variables[item]

    def __setitem__(self, key, value):
        if key not in Config.VARIABLE_NAMES:
            raise KeyError(f"{key} is not valid. Must be one of: {Config.VARIABLE_NAMES}")
        self.variables[key] = value

    def __str__(self):
        return str(self.variables)

    def write(self):
        def is_backend_variable(name):
            return name in {"region", "bucket"}

        os.makedirs(".terraform", exist_ok=True)
        with open(".terraform/ci-backend-config", "w") as f:
            for var_name, value in self.variables.items():
                if value and is_backend_variable(var_name):
                    f.write(f'{var_name}="{value}"\n')

        with open("terraform.tfvars", "w") as f:
            for var_name, value in self.variables.items():
                if value and (var_name == "region" or not is_backend_variable(var_name)):
                    f.write(f'{var_name}="{value}"\n')

    @classmethod
    def create_from_args(cls, args):
        config = Config()
        for var_name in Config.VARIABLE_NAMES:
            value = getattr(args, var_name)
            if value:
                config[var_name] = value
        return config

    @classmethod
    def add_args(cls, parser):
        for var_name in Config.VARIABLE_NAMES:
            parser.add_argument("--{var_name}".format(var_name=var_name.replace("_", "-")))


def s3_remote_state_bucket(config, region, session):
    # Ensure bucket exists for remote state
    if config["bucket"] is None:
        sts = session.client("sts")
        config["bucket"] = (
            "bai-ci-terraform-remote-state-" + sts.get_caller_identity()["Account"] + "-" + session.region_name
        )

    s3 = session.resource("s3")
    bucket_name = config["bucket"]
    bucket = s3.Bucket(bucket_name)
    bucket.load()
    if bucket.creation_date is None:
        print(f"Will create a bucket named `{bucket_name}` in region `{region}`")

        try:
            if region == "us-east-1":
                # https://github.com/boto/boto3/issues/125#issuecomment-109408790
                bucket.create()
            else:
                bucket.create(CreateBucketConfiguration={"LocationConstraint": region})
        except Exception as e:
            raise


def chime_hook_url(config, session):
    if config["chime_hook_url"]:
        return

    secrets_manager_client = session.client(service_name="secretsmanager")
    try:
        hook_url_secret = secrets_manager_client.get_secret_value(SecretId="ChimeHookUrl")
        config["chime_hook_url"] = hook_url_secret["SecretString"]
    except secrets_manager_client.exceptions.ResourceNotFoundException:
        pass


def file_replace_line(file_path, str_find, str_replace):
    """ Replace line <str_find> with <str_replace> in the file located at <file_path>
    """
    tmp_file_path = file_path + ".tmp"
    with open(file_path, "r") as file_orig, open(tmp_file_path, "w") as file_new:
        for line in file_orig:
            file_new.write(line.replace(str_find, str_replace))

    shutil.move(tmp_file_path, file_path)


def load_cookies_from_mozilla(filename):
    """ Loads cookies from the file saved in Netscape format (e.g. curl saves in this format)
    Returns MozillaCookieJar object
    """
    import tempfile
    from http.cookiejar import MozillaCookieJar
    from http.cookiejar import Cookie

    if not os.path.isfile(filename):
        return None

    tmp_file = tempfile.NamedTemporaryFile()
    tmp_file.close()
    tmp_file_path = tmp_file.name
    shutil.copy(filename, tmp_file_path)

    file_replace_line(tmp_file_path, "#HttpOnly_", "")  # Cheating: just remove HttpOnly_ flag
    file_replace_line(
        tmp_file_path, "\r", ""
    )  # if created on Windows, cookie value will have \r at the end on Linux which breaks SSL connection with midway-auth

    ns_cookiejar = MozillaCookieJar()
    ns_cookiejar.load(tmp_file_path, ignore_discard=True, ignore_expires=True)
    os.remove(tmp_file_path)

    for c in ns_cookiejar:
        args = dict(vars(c).items())
        args["rest"] = args["_rest"]
        del args["_rest"]
        c = Cookie(**args)
        epoch_time = int(time())
        if c.expires > 0 and c.expires < epoch_time:
            raise ValueError("cookie is expired. Please run mwinit")
        if c.expires == 0:
            c.expires = None  # convert curl format to python cookie format
        ns_cookiejar.set_cookie(c)

    return ns_cookiejar


def prefix_list_id(config):
    if config["prefix_list_id"]:
        return

    region = config["region"]
    jar = load_cookies_from_mozilla(str(Path.home() / ".midway/cookie"))
    response = requests.get(f"https://apll.corp.amazon.com/?region={region}&format=json", cookies=jar, verify=False)
    result = json.loads(response.text)
    config["prefix_list_id"] = result["result"]["com.amazonaws.firewall.regional-corp-only"]


def main():
    description = textwrap.dedent(
        """\
        An utility script that is meant to replace calling `terraform init`.

        It takes care of creating the S3 Bucket so that Terraform knows how to handle remote state. Also, the CI's
        Terraform code accepts parameters (eg.: branch name), which this script writes to the `terraform.tfvars` file.

        The default values are meant to reference the `master` branch of MXNetEdge/benchmark-ai.
        """
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--clean", action="store_true", help="Removes current state and configured values")
    Config.add_args(parser)
    args = parser.parse_args()
    if args.clean:
        remove_terraform_config_files()
        return

    config = Config.create_from_args(args)
    region = config["region"]
    session = boto3.Session(region_name=region)

    chime_hook_url(config, session)
    s3_remote_state_bucket(config, region, session)
    prefix_list_id(config)

    config.write()

    print("=> Configuration to call terraform with:")
    print(config)

    print("=> Calling `terraform init`")
    ret = subprocess.call(["terraform", "init", "-backend-config=.terraform/ci-backend-config"])

    if "GITHUB_TOKEN" not in os.environ:
        print("!!! ATTENTION !!!")
        print("Don't forget to set the environment variable `GITHUB_TOKEN` before `terraform apply`.")
        print("This is a limitation of the AWS Terraform provider (HACK!!!)")
        print(
            "Follow this page for instructions: https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line"
        )
    return ret


def remove_terraform_config_files():
    def rm(path):
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed `{path}`")

    rm(".terraform/terraform.tfstate")
    rm(".terraform/ci-backend-config")
    rm("terraform.tfvars")


if __name__ == "__main__":
    main()
