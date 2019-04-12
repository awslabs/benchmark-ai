import os
import pycurl
import tempfile
from urllib.parse import urlparse

import argparse
import boto3
import kazoo.client
import kazoo.client


class UploadProgress:
    def __init__(self):
        self.progress = 0

    def increment(self, package_size):
        self.progress += package_size
        print(f"{self.progress} bytes uploaded so far")


def s3_to_s3_deep(src_bucket, src_key, dst_bucket, dst_key):
    s3 = boto3.resource('s3')
    old_bucket = s3.Bucket(src_bucket)
    new_bucket = s3.Bucket(dst_bucket)

    for obj in old_bucket.objects.filter(Prefix=src_key):
        old_source = {'Bucket': src_bucket,
                      'Key': obj.key}
        # replace the prefix
        new_key = obj.key.replace(src_key, dst_key)
        new_obj = new_bucket.Object(new_key)
        new_obj.copy(old_source)


def s3_to_s3(args):
    dst = urlparse(args.dst)

    dst_bucket = dst.netloc
    dst_key = dst.path[1:]

    src = urlparse(args.src)
    src_bucket = src.netloc
    src_key = src.path[1:]

    s3_to_s3_deep(src_bucket, src_key, dst_bucket, dst_key)


def progress(download_t, download_d, upload_t, upload_d):
    print(f"{download_d} out of {download_t}")


def http_to_s3(args):
    print("http to s3")
    dst = urlparse(args.dst)

    bucket = dst.netloc
    key = dst.path[1:]

    print(f"bucket {bucket} key {key}")

    with tempfile.TemporaryFile("r+b") as fp:
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, args.src)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 300)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, progress)
        curl.setopt(pycurl.WRITEDATA, fp)

        print("Start download")
        curl.perform()
        print("End download")

        fp.seek(0)
        print("Start upload")
        boto3.client('s3').upload_fileobj(fp, bucket, key)
        print("End upload")


STATE_RUNNING = "RUNNING".encode('utf-8')
STATE_DONE = "DONE".encode('utf-8')
STATE_FAILED = "FAILED".encode('utf-8')


# Current version doesn't stream - we create temporary files.
def fetch(args):
    print(f"Fetch job = {args}\n")

    src_scheme = urlparse(args.src)
    if src_scheme.scheme == "http" or src_scheme.scheme == "https":
        http_to_s3(args)
    elif src_scheme.scheme == "s3":
        s3_to_s3(args)

    if args.zk_node_path:
        zk = kazoo.client.KazooClient(hosts=os.environ.get("ZOOKEEPER_ENSEMBLE_HOSTS"))
        zk.start()
        zk.set(args.zk_node_path, STATE_DONE)
        zk.stop()


def main():
    parser = argparse.ArgumentParser(description='Downloads the dataset from http/ftp/s3 to internal s3')

    parser.add_argument('--src', required=True,
                        help='Source', default=None)
    parser.add_argument('--dst', metavar='dst', required=True,
                        help='Destination', default=None)
    parser.add_argument('--md5',
                        help='MD5 hash', default=None)
    parser.add_argument('--zk-node-path',
                        help='Zookeeper node to update', default=None)

    args = parser.parse_args()

    fetch(args)


if __name__ == '__main__':
    main()
