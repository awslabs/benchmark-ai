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
        metrics: List[Metric] = []
        if not self.environment:
            return metrics
        json_object = json.loads(self.environment)
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
            logger.info(f"no metrics requested")
            return
        for metric in options.metrics:
            self.add_metric(metric)

    def add_metric(self, metric: Metric):
        self.metrics[metric] = re.compile(base64.b64decode(metric.pattern).decode("utf-8"))

    def listen(self):
        if not self.metrics:
            logger.info(f"no metrics requested")
            return

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
