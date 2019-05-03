from baictl.__main__ import main


def test_get_infra():
    assert 0 == main("baictl get infra".split(" "))
