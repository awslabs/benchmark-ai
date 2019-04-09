from kafka import KafkaConsumer
import kazoo.client
import json
import hashlib
import kubernetes
import string
import random

import pycurl
import logging

import os

def estimate_content_length(url):
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.NOBODY, 1)
    c.perform()
    return c.getinfo(c.CONTENT_LENGTH_DOWNLOAD)

def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

KUBECONFIG = os.environ.get("KUBECONFIG")

kubernetes.config.load_kube_config(KUBECONFIG)

configuration = kubernetes.client.Configuration()
api_instance = kubernetes.client.BatchV1Api(kubernetes.client.ApiClient(configuration))

def start_download(task):
    download_job = kubernetes.client.V1Job(api_version="batch/v1", kind="Job")

    download_job.metadata = kubernetes.client.V1ObjectMeta(namespace="default", name="download-" + id_generator())
    download_job.status = kubernetes.client.V1JobStatus()
    # Now we start with the Template...
    template = kubernetes.client.V1PodTemplate()
    template.template = kubernetes.client.V1PodTemplateSpec()

    job_args=[task.src, task.dst]

    container = kubernetes.client.V1Container(name="downloader", image="stsukrov/datafetcher",args=job_args)
    template.template.spec = kubernetes.client.V1PodSpec(containers=[container], restart_policy='Never', node_selector={"node.type":"bai-services"})
    # And finally we can create our V1JobSpec!
    download_job.spec = kubernetes.client.V1JobSpec(ttl_seconds_after_finished=600, template=template.template)

    resp = api_instance.create_namespaced_job("default", download_job, pretty=True)
    print(resp)


def md5(src):
    md5hash = hashlib.md5()
    md5hash.update(src.encode('utf-8'))
    return md5hash.hexdigest()


def url_to_key(src):
    return "/datasets/" + md5(src)


ZOOKEPER_ENSEBLE_HOSTS = os.environ.get("ZOOKEPER_ENSEBLE_HOSTS")

STATE_RUNNING = "RUNNING".encode('utf-8')
STATE_DONE = "DONE".encode('utf-8')
STATE_FAILED = "FAILED".encode('utf-8')


class DownloadTask:
    def __init__(self, src, dst, md5):
        self.src = src
        self.dst = dst
        self.md5 = md5


zk = kazoo.client.KazooClient(hosts=ZOOKEPER_ENSEBLE_HOSTS)
zk.start()

def dict_to_task(task):
    return DownloadTask(task["src"], task["dst"], task.get("md5", ""))

def extract_tasks(msg):
    return list(map(dict_to_task, msg.value))


def _on_zk_changed(event, callback):
    on_zk_changed = lambda event: _on_zk_changed(event, callback)
    node_data = zk.get(event.path, on_zk_changed)
    if node_data[0] == STATE_DONE:
        callback()


def execute(task, callback):
    zkpath = url_to_key(task.src)
    try:
        zk.create(zkpath, STATE_RUNNING, makepath=True)

        start_download(task)
    except kazoo.exceptions.NodeExistsError:
        on_zk_changed = lambda event: _on_zk_changed(event, callback)
        node_data = zk.get(zkpath, on_zk_changed)
        if node_data[0] == STATE_DONE:
            callback()


def execute_all(tasks, callback):

    cb = lambda: callback()
    for tsk in tasks:
        execute(tsk, cb)


def handle_msg(msg):
    tasks = extract_tasks(msg)

    cb = lambda: print("done")
    execute_all(tasks, cb)


BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS").split(',')
BENCHMARK_TOPIC = os.environ.get("KAFKA_TOPIC")

json_deserializer = lambda m: json.loads(m.decode('utf-8'))

consumer = KafkaConsumer(BENCHMARK_TOPIC, bootstrap_servers=BOOTSTRAP_SERVERS, value_deserializer=json_deserializer)

for msg in consumer:
    handle_msg(msg)
