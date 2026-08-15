"""Pinned-runtime time determinism audit for the new release gate."""

import time


PROBE = "contracts/time_determinism_probe.py"


def test_host_wall_clock_does_not_change_pinned_genvm_state(direct_vm, direct_deploy):
    direct_vm.warp("2040-01-01T00:00:00Z")
    probe = direct_deploy(PROBE)
    first = probe.sample()
    assert direct_vm.run_validator()

    time.sleep(1.1)
    second = probe.sample()
    assert direct_vm.run_validator()

    assert first == second == {
        "timestamp": 2208988800,
        "marker": "pinned-genvm-time",
    }
