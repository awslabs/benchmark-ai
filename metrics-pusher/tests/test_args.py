from bai_metrics_pusher.args import get_input, InputValue

ALL_ARGS = f"--backend stdout --pod-namespace pod-namespace --pod-name pod-name "


def test_get_input():
    expected_cfg = InputValue(backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={})
    cfg = get_input(ALL_ARGS)
    assert cfg == expected_cfg


def test_get_input_with_many_backend_args():
    expected_cfg = InputValue(
        backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={"key": "value"}
    )
    cfg = get_input(ALL_ARGS, environ={"BACKEND_ARG_KEY": "value"})
    assert cfg == expected_cfg
