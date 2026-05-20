from futureagi_sdk_test_harness.contract import load_contract


def test_load_default_contract():
    contract = load_contract()
    assert contract.name == "futureagi-sdk-compliance"
    assert {suite["id"] for suite in contract.suites} >= {
        "auth_raw_request",
        "annotation_bulk_log",
    }
