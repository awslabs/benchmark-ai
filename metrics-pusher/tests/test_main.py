from bai_metrics_pusher.args import InputValue


def test_main(mocker, monkeypatch):
    mock_start_loop = mocker.patch("bai_metrics_pusher.loop.start_loop")
    from bai_metrics_pusher.__main__ import main

    monkeypatch.setenv("BACKEND_ARG_JOB_ID", "123")
    main("--backend stdout --pod-namespace pod-namespace --pod-name pod-name ")

    expected_input = InputValue(
        backend="stdout", pod_name="pod-name", pod_namespace="pod-namespace", backend_args={"job_id": "123"}
    )

    mock_start_loop.assert_called_with(expected_input)
