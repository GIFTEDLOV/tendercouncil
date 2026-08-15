"""Test-only proof that pinned GenVM time is independent of host wall time."""

import datetime

from genlayer import *


class TimeDeterminismProbe(gl.Contract):
    @gl.public.write
    def sample(self):
        def leader_fn():
            return {
                "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
                "marker": "pinned-genvm-time",
            }

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            current = {
                "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
                "marker": "pinned-genvm-time",
            }
            return leader_result.calldata == current

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
