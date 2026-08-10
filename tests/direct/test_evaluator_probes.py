import json
import warnings


PROBE = "contracts/evaluator_probe.py"
FIXTURE_URL = "https://fixture.invalid/immutable.txt"


def _assert_callbacks_cloudpickle(direct_vm):
    import cloudpickle

    _, leader_fn, validator_fn = direct_vm._captured_validators[-1]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cloudpickle.dumps(leader_fn)
        cloudpickle.dumps(validator_fn)
    assert not [item for item in caught if "storage class" in str(item.message).lower()]


def _mock_d(direct_vm):
    direct_vm.mock_web(FIXTURE_URL, {"status": 200, "body": "immutable fixture"})
    direct_vm.mock_llm(
        r"Return JSON with exactly",
        '{"probe":"D","supported":true}',
    )


def test_probe_a_constant_boundary(direct_vm, direct_deploy):
    contract = direct_deploy(PROBE)
    assert contract.probe_a() == {"probe": "A", "value": 7}
    assert direct_vm.run_validator()
    _assert_callbacks_cloudpickle(direct_vm)


def test_probe_b_web_boundary(direct_vm, direct_deploy):
    direct_vm.mock_web(FIXTURE_URL, {"status": 200, "body": "immutable fixture"})
    contract = direct_deploy(PROBE)
    assert contract.probe_b(FIXTURE_URL)["body"] == "immutable fixture"
    assert direct_vm.run_validator()
    _assert_callbacks_cloudpickle(direct_vm)


def test_probe_c_llm_boundary(direct_vm, direct_deploy):
    direct_vm.mock_llm(
        r"Return JSON with exactly",
        '{"probe":"C","value":11}',
    )
    contract = direct_deploy(PROBE)
    assert contract.probe_c() == {"probe": "C", "value": 11}
    assert direct_vm.run_validator()
    _assert_callbacks_cloudpickle(direct_vm)


def test_probe_d_web_plus_llm_boundary(direct_vm, direct_deploy):
    _mock_d(direct_vm)
    contract = direct_deploy(PROBE)
    assert contract.probe_d(FIXTURE_URL) == {
        "probe": "D",
        "body_len": len("immutable fixture"),
        "supported": True,
    }
    assert direct_vm.run_validator()
    _assert_callbacks_cloudpickle(direct_vm)


def test_probe_e_captured_immutable_strings(direct_vm, direct_deploy):
    direct_vm.mock_web(FIXTURE_URL, {"status": 200, "body": "immutable fixture"})
    direct_vm.mock_llm(
        r"Return JSON with exactly",
        '{"probe":"E","supported":true}',
    )
    contract = direct_deploy(PROBE)
    assert contract.probe_e(FIXTURE_URL, "locked tender", "locked bid") == {
        "probe": "E",
        "supported": True,
        "body_len": len("immutable fixture"),
    }
    assert direct_vm.run_validator()
    _assert_callbacks_cloudpickle(direct_vm)


def test_probe_f_actual_evaluator_shape(direct_vm, direct_deploy):
    direct_vm.mock_web(FIXTURE_URL, {"status": 200, "body": "immutable fixture"})
    direct_vm.mock_llm(
        r"Return JSON with exactly",
        '{"decision":"ACCEPT","score":80,"evidence_count":1}',
    )
    contract = direct_deploy(PROBE)
    source_json = json.dumps([{"uri": FIXTURE_URL}], sort_keys=True)
    assert contract.probe_f(FIXTURE_URL, "locked tender", "locked bid", source_json) == {
        "decision": "ACCEPT",
        "score": 80,
        "evidence_count": 1,
    }
    assert direct_vm.run_validator()
    _assert_callbacks_cloudpickle(direct_vm)
