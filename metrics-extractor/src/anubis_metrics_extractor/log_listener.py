#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import json
import logging
import re
from collections import namedtuple
from dataclasses import dataclass
from typing import List, Optional

from kubernetes import client

from benchmarkai import emit

logger = logging.getLogger("metrics-extractor")
Pattern = type(re.compile("", 0))

Metric = namedtuple("Metric", ["name", "pattern"])


@dataclass
class LogExtractorOptions:
    pod_name: str
    pod_namespace: str
    metrics: List[Metric]
    pod_container: Optional[str]


@dataclass
class EnvironmentReader:
    environment: str

    def get_metrics(self) -> List[Metric]:
        json_object = json.loads(self.environment)
        metrics: List[Metric] = []
        if isinstance(json_object, list):
            for m_object in json_object:
                metrics.append(Metric(**m_object))
        else:
            metrics.append(Metric(**json_object))
        return metrics


class LogExtractor:
    def __init__(self, options: LogExtractorOptions):
        self.options: LogExtractorOptions = options
        self.metrics = {}
        if not options.metrics:
            raise ValueError("At least 1 metric should be defined")
        for metric in options.metrics:
            self.add_metric(metric)

    def add_metric(self, metric: Metric):
        self.metrics[metric] = re.compile(base64.b64decode(metric.pattern).decode("utf-8"))

    def listen(self):
        v1 = client.CoreV1Api()
        if self.options.pod_container:
            stream = v1.read_namespaced_pod_log(
                name=self.options.pod_name,
                namespace=self.options.pod_namespace,
                follow=True,
                _preload_content=False,
                container=self.options.pod_container,
            ).stream()
        else:
            stream = v1.read_namespaced_pod_log(
                name=self.options.pod_name, namespace=self.options.pod_namespace, follow=True, _preload_content=False
            ).stream()

        for line in stream:
            line = line.decode("utf-8")
            for metric, pattern in self.metrics.items():
                for m in pattern.findall(line):
                    emit({metric.name: m})
                    logger.debug(f"match: {metric.name}{m}")
