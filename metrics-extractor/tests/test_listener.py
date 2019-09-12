#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from anubis_metrics_extractor.log_listener import EnvironmentReader


def test_empty():
    reader = EnvironmentReader("")
    metrics = reader.get_metrics()
    assert len(metrics) == 0


patterns = dict(one="Lio=", another="Lis=", digit="XGQ=")  # .* | .+ | \d


def test_single():
    reader = EnvironmentReader('{{"name": "mama", "pattern": "{}", "units": "$"}}'.format(patterns["one"]))
    metrics = reader.get_metrics()
    assert len(metrics) == 1

    metric = metrics[0]
    assert metric.name == "mama"
    assert metric.pattern == patterns["one"]
    assert metric.units == "$"


def test_incomplete():
    with pytest.raises(TypeError):
        reader = EnvironmentReader('{"name": "mama"}')
        _ = reader.get_metrics()


def test_multiple():
    reader = EnvironmentReader(
        '[{{"name": "mama", "pattern": "{}", "units": "sec"}}, '
        '{{"name": "papa", "pattern": "{}", "units": "%"}}]'.format(patterns["one"], patterns["another"])
    )
    metrics = reader.get_metrics()
    assert len(metrics) == 2

    metric = metrics[0]
    assert metric.name == "mama"
    assert metric.pattern == patterns["one"]
    assert metric.units == "sec"

    metric = metrics[1]
    assert metric.name == "papa"
    assert metric.pattern == patterns["another"]
    assert metric.units == "%"


def test_bad_json():
    with pytest.raises(ValueError):
        reader = EnvironmentReader('[{"name": "mama", "')
        _ = reader.get_metrics()


def test_json_escape():
    reader = EnvironmentReader('{{"name": "mama", "pattern": "{}", "units": "%"}}'.format(patterns["digit"]))
    metrics = reader.get_metrics()
    assert len(metrics) == 1

    metric = metrics[0]
    assert metric.name == "mama"
    assert metric.pattern == patterns["digit"]
