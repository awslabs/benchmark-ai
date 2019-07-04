from bai_k8s_utils.service_labels import ServiceLabels

ACTION_ID = "ACTION_ID"
CLIENT_ID = "CLIENT_ID"
SOME_SERVICE = "SOME_SERVICE"


def test_get_label_selector():
    assert (
        ServiceLabels.get_label_selector(SOME_SERVICE, CLIENT_ID, ACTION_ID)
        == f"{ServiceLabels.CREATED_BY_LABEL}={SOME_SERVICE},"
        + f"{ServiceLabels.CLIENT_ID_LABEL}={CLIENT_ID},"
        + f"{ServiceLabels.ACTION_ID_LABEL}={ACTION_ID}"
    )


def test_get_label_selector_all_actions():
    assert (
        ServiceLabels.get_label_selector(SOME_SERVICE, CLIENT_ID)
        == f"{ServiceLabels.CREATED_BY_LABEL}={SOME_SERVICE}," + f"{ServiceLabels.CLIENT_ID_LABEL}={CLIENT_ID}"
    )


def test_labels():
    assert ServiceLabels.get_labels(SOME_SERVICE, CLIENT_ID, ACTION_ID) == {
        ServiceLabels.ACTION_ID_LABEL: ACTION_ID,
        ServiceLabels.CLIENT_ID_LABEL: CLIENT_ID,
        ServiceLabels.CREATED_BY_LABEL: SOME_SERVICE,
    }
