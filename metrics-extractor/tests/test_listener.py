#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from anubis_metrics_extractor.log_listener import EnvironmentReader


def test_empty():
    with pytest.raises(ValueError):
        reader = EnvironmentReader("")
        _ = reader.get_metrics()


patterns = dict(one="Lio=", another="Lis=", digit="XGQ=")  # .* | .+ | \d


def test_single():
    reader = EnvironmentReader('{{"name": "mama", "pattern": "{}"}}'.format(patterns["one"]))
    metrics = reader.get_metrics()
    assert len(metrics) == 1

    metric = metrics[0]
    assert metric.name == "mama"
    assert metric.pattern == patterns["one"]


def test_incomplete():
    with pytest.raises(TypeError):
        reader = EnvironmentReader('{"name": "mama"}')
        _ = reader.get_metrics()


def test_multiple():
    reader = EnvironmentReader(
        '[{{"name": "mama", "pattern": "{}"}}, {{"name": "papa", "pattern": "{}"}}]'.format(
            patterns["one"], patterns["another"]
        )
    )
    metrics = reader.get_metrics()
    assert len(metrics) == 2

    metric = metrics[0]
    assert metric.name == "mama"
    assert metric.pattern == patterns["one"]

    metric = metrics[1]
    assert metric.name == "papa"
    assert metric.pattern == patterns["another"]


def test_bad_json():
    with pytest.raises(ValueError):
        reader = EnvironmentReader('[{"name": "mama", "')
        _ = reader.get_metrics()


def test_json_escape():
    reader = EnvironmentReader('{{"name": "mama", "pattern": "{}"}}'.format(patterns["digit"]))
    metrics = reader.get_metrics()
    assert len(metrics) == 1

    metric = metrics[0]
    assert metric.name == "mama"
    assert metric.pattern == patterns["digit"]
