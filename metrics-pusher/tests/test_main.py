from bai_metrics_pusher.args import InputValue


def test_main(mocker):
    mock_start_loop = mocker.patch("bai_metrics_pusher.loop.start_loop")
    from bai_metrics_pusher.__main__ import main

    main("--backend stdout --pod-namespace pod-namespace --pod-name pod-name ")

    expected_input = InputValue(
        backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={"labels": {}}
    )

    mock_start_loop.assert_called_with(expected_input)
