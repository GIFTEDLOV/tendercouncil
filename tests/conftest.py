"""Repository-wide Windows-safe test process guards."""

import os
import sys

import pytest
from gltest.direct.loader import create_address
from gltest.direct.vm import VMContext


def pytest_configure():
    # Contract/tool output may contain UTF-8. Console encoding is tooling state,
    # never a reason to change contract semantics or fixture content.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


@pytest.fixture(autouse=True)
def windows_stdin_guard():
    """Restore fd 0 after gltest's repeated Windows calldata injections.

    genlayer-test 0.29.2 replaces stdin once per deployed contract but retains
    only the newest backup descriptor. Restoring the test's original handle at
    teardown releases the temporary files before the plugin's atexit cleanup.
    """
    original = os.dup(0)
    try:
        yield
    finally:
        os.dup2(original, 0)
        os.close(original)


@pytest.fixture
def direct_vm(windows_stdin_guard) -> VMContext:
    """Override the upstream fixture so its cleanup precedes our fd-0 guard."""
    context = VMContext()
    context.sender = create_address("default_sender")
    with context.activate():
        yield context
