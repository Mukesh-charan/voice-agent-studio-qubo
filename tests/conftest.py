"""
tests/conftest.py
Skip integration tests that require the full server stack (server.py imports
Twilio, edge-tts, faster-whisper, etc.) when those packages are not installed.
"""
import sys
import pytest


def pytest_collection_modifyitems(config, items):
    """Skip tests in test_booking_concurrent, test_twilio, test_api_guardrails_google,
    and test_guardrail_google when 'server' is not importable."""
    skip_server = pytest.mark.skip(
        reason="Requires full server stack (server.py + Twilio/edge-tts/faster-whisper). "
               "Install all requirements.txt deps and re-run to execute integration tests."
    )
    for item in items:
        module_name = item.module.__name__
        if module_name in (
            "tests.test_booking_concurrent",
            "test_booking_concurrent",
            "tests.test_twilio",
            "test_twilio",
            "tests.test_api_guardrails_google",
            "test_api_guardrails_google",
            "tests.test_guardrail_google",
            "test_guardrail_google",
            "tests.test_kb_upload",
            "test_kb_upload",
        ):
            try:
                import importlib
                importlib.import_module("server")
            except ImportError:
                item.add_marker(skip_server)

