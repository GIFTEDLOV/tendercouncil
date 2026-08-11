# Bradbury canonical-demo policy

The Core contract keeps a configurable protocol minimum of 600 seconds so
local tests can use bounded clocks. The canonical live Bradbury five-bid demo
must use `7200` seconds (`tools/demo_policy.py`), not the minimum. Bradbury
non-deterministic finality has been observed at approximately 1,800 seconds;
the larger window provides meaningful margin before a provisional award can
advance toward review, award, or settlement.

This is a live-demo configuration, not a consensus or product-policy
constant. The product default should remain materially longer, such as 24
hours, for real procurement.
