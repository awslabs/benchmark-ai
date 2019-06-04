"""
A script to manipulate the `aws-auth` configmap that is created by EKS.

See the docs for more info: https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html
"""
import sys
import tempfile

from typing import List

import subprocess
from ruamel import yaml
from argparse import ArgumentParser


class AwsAuthConfigMap:
    def __init__(self):
        aws_auth_configmap_string = subprocess.check_output(
            "kubectl get -n kube-system configmap/aws-auth -o yaml", shell=True
        )
        self.aws_auth_configmap = yaml.load(aws_auth_configmap_string, Loader=yaml.Loader)
        assert len(aws_auth_configmap_string) > 0
        self.aws_auth_configmap["data"] = self._deserialize_data_items()
        self.aws_auth_configmap["metadata"] = {
            "name": "aws-auth",
            "namespace": "kube-system",
            "selfLink": "/api/v1/namespaces/kube-system/configmaps/aws-auth",
        }

    def add_role(self, arn: str, username: str, groups: List[str]):
        self._add_item_to_data("mapRoles", "rolearn", arn, groups, username)

    def add_iam_user(self, arn: str, username: str, groups: List[str]):
        self._add_item_to_data("mapUsers", "userarn", arn, groups, username)

    def apply(self):
        with tempfile.NamedTemporaryFile(prefix="new-aws-auth", mode="w+") as f:
            contents = self._serialize()
            print("##### Will apply this new configmap:")
            print(contents)
            f.write(contents)
            f.flush()
            subprocess.check_output("kubectl apply -f {}".format(f.name), shell=True)

    def _deserialize_data_items(self):
        return {
            key_name: yaml.load(value, Loader=yaml.Loader) or []
            for key_name, value in self.aws_auth_configmap["data"].items()
        }

    def _add_item_to_data(self, key_name, arn_key_name: str, arn: str, groups: List[str], username: str):
        data = self.aws_auth_configmap["data"]
        list_with_items = data[key_name]
        for item in list_with_items:
            if arn == item[arn_key_name]:
                return

        item = {arn_key_name: arn, "username": username, "groups": groups}
        list_with_items.append(item)

    def _serialize(self):
        ret = dict(self.aws_auth_configmap)
        for key_name, item in self.aws_auth_configmap["data"].items():
            serialized_value = ""
            if len(item) > 0:
                serialized_value = yaml.dump(item, Dumper=yaml.RoundTripDumper, default_flow_style=False)
            ret["data"][key_name] = serialized_value
        return yaml.dump(ret, Dumper=yaml.RoundTripDumper)


def main(args=None):
    parser = ArgumentParser()
    role_group = parser.add_argument_group("role")
    role_group.add_argument("--role-arn")
    role_group.add_argument("--role-username")
    role_group.add_argument("--role-groups", nargs="*")

    iam_user_group = parser.add_argument_group("iam-user")
    iam_user_group.add_argument("--iam-user-arn")
    iam_user_group.add_argument("--iam-user-username")
    iam_user_group.add_argument("--iam-user-groups", nargs="*")
    args = parser.parse_args(args)

    aws_auth_configmap = AwsAuthConfigMap()

    if args.role_arn:
        aws_auth_configmap.add_role(args.role_arn, args.role_username, args.role_groups)

    if args.iam_user_arn:
        aws_auth_configmap.add_iam_user(args.iam_user_arn, args.iam_user_username, args.iam_user_groups)

    aws_auth_configmap.apply()

    return 0


if __name__ == "__main__":
    sys.exit(main())
