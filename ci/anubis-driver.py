#!/usr/bin/env python3
import json
import os
import requests
import urllib3
import shutil
import textwrap
import subprocess
import argparse
import boto3
import sys
from pyfiglet import Figlet
from pathlib import Path
from collections import namedtuple
from time import time
from typing import Dict


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
        "extra_users",
        "extra_roles",
    }

    def __init__(self):
        existing_values = {}
        existing_values.update(open_terraform_vars_file(".terraform/ci-backend-config"))
        existing_values.update(open_terraform_vars_file("terraform.tfvars"))

        self.variables = {}
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
            if var_name == "region" or var_name == "prefix_list_id":
                parser.add_argument("--{var_name}".format(var_name=var_name.replace("_", "-")), required=True)
            else:
                parser.add_argument("--{var_name}".format(var_name=var_name.replace("_", "-")))


def s3_remote_state_bucket(config, region, session):
    # Ensure bucket exists for remote state
    sts = session.client("sts")
    if os.path.exists(".terraform/ci-backend-config"):
        ci_backend_config = open(".terraform/ci-backend-config", "r").read()
        if sts.get_caller_identity()["Account"] not in ci_backend_config:
            os.remove(".terraform/ci-backend-config")
            config["bucket"] = None
            if os.path.exists(".terraform/terraform.tfstate"):
                os.remove(".terraform/terraform.tfstate")

    if config["bucket"] is None:
        config["bucket"] = "bai-ci-terraform-state-" + sts.get_caller_identity()["Account"] + "-" + session.region_name

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


def main():
    print(Figlet().renderText("anubis setup"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Removes current state and configured values")
    parser.add_argument("--destroy", action="store_true", help="Removes current state and configured values")
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
    config.write()

    print("=> Configuration to call terraform with:")
    print(config)
    mode = "destroy" if args.destroy else "create"
    user_response = input(f"Do you want to {mode} the pipeline with this configuration? ([y]/n)?: ").lower().strip()
    if not user_response == "y" and not user_response == "yes" and not user_response == "":
        sys.exit()
    print("=> Calling `terraform init`")
    return_code = subprocess.call(["terraform", "init", "-backend-config=.terraform/ci-backend-config"])
    if return_code != 0:
        raise Exception(f"Failure to init terraform: {return_code}")

    # Destroy pipeline and infrastructure
    if args.destroy:
        destroy_pipeline(region)
        destroy_infrastructure()
        return

    if "GITHUB_TOKEN" not in os.environ:
        print("!!! ATTENTION !!!")
        print("Don't forget to set the environment variable `GITHUB_TOKEN` before `terraform apply`.")
        print("This is a limitation of the AWS Terraform provider (HACK!!!)")
        print(
            "Follow this page for instructions: https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line"
        )
        return 1

    # Create pipeline which creates infrastructure and deploys services
    print("=> Calling `terraform plan`")
    return_code = subprocess.call(["terraform", "plan", "--out=terraform.plan"])

    if return_code != 0:
        raise Exception(f"Failure calling `terraform plan`: {return_code}")
    print("=> Calling `terraform apply`")
    return_code = subprocess.call(["terraform", "apply", "terraform.plan"])
    if return_code != 0:
        raise Exception(f"Failure calling `terraform plan`: {return_code}")

    return


def remove_terraform_config_files():
    def rm(path):
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed `{path}`")

    rm(".terraform/terraform.tfstate")
    rm(".terraform/ci-backend-config")
    rm("terraform.tfvars")
    rm("terraform.plan")


def destroy_pipeline(region):
    # HACK: Rules don't get revoked causing timeout on security group destroy
    group_id = subprocess.check_output(["terraform", "output", "blackbox_vpc_default_group_id"]).strip()
    source_group = subprocess.check_output(["terraform", "output", "blackbox_public_group_id"]).strip()
    return_code = subprocess.call(
        [
            "aws",
            "ec2",
            "revoke-security-group-ingress",
            "--region",
            region,
            "--group-id",
            group_id,
            "--source-group",
            source_group,
            "--protocol",
            "all",
        ]
    )
    print("=> Calling `terraform destroy` to destroy pipeline")
    return_code = subprocess.call(["terraform", "destroy", "-auto-approve"])
    if return_code != 0:
        raise Exception(f"Failure calling `terraform destroy`: {return_code}")


def destroy_infrastructure():
    print("=> Calling `make destroy` in baictl to destroy infrastructure")
    return_code = subprocess.call(["make", "destroy"], cwd="../baictl")
    if return_code != 0:
        raise Exception(f"Failure calling `make destroy` in baictl: {return_code}")


if __name__ == "__main__":
    main()
