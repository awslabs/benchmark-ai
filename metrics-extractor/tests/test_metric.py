#!/usr/bin/env python
# -*- coding: utf-8 -*-


from anubis_metrics_extractor.log_listener import Metric


def test_hashable():
    metric = Metric(name="name", pattern="pattern", units="%")
    d = {metric: 1}
    assert d[metric] == 1
