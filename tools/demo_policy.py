"""Non-protocol demo policy for the future Bradbury canonical E2E."""

# Bradbury non-deterministic finality has been observed near 1,800 seconds.
# Keep meaningful margin for the live response window; this is not the Core's
# minimum and does not change the protocol's configurable lower bound.
BRADBURY_DEMO_RESPONSE_WINDOW_SECONDS = 7200

