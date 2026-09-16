"""Shared test fixtures for the APSPOT lambdas.

The lambda modules read configuration from environment variables *at import
time* and `import boto3` at module level (boto3 is provided by the AWS Lambda
runtime, not vendored). We set the env vars and stub boto3 here, before any
lambda module is imported, so the suite runs on a bare interpreter with only
`requests` and `pytest` installed. This is what lets us run the same tests
under python3.9 and python3.12/3.13 to prove runtime compatibility.
"""
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make lambdas/ importable as top-level modules (matches the Lambda handler
# path, e.g. lambdas/processmessage.py -> handler "lambdas/processmessage...").
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "lambdas"))

# Config the modules expect at import time (values mirror config/*.yml shapes).
os.environ.setdefault("pota_api_url", "https://api.pota.test")
os.environ.setdefault("pota_api_dev_url", "https://devapi.pota.test")
os.environ.setdefault("pnp_api_url", "https://pnp.test/api")
os.environ.setdefault("pnp_api_user_id", "APSPOT")
os.environ.setdefault("pnp_api_user_key", "TESTKEY")
os.environ.setdefault("APSPOTAPIURL", "https://apspot.test")

# Stub boto3 so `import boto3` succeeds and boto3.client(...) is a no-op mock.
if "boto3" not in sys.modules:
    boto3_stub = types.ModuleType("boto3")
    boto3_stub.client = MagicMock(name="boto3.client")
    sys.modules["boto3"] = boto3_stub


class FakeResponse:
    """Minimal stand-in for requests.Response as the lambdas use it."""

    def __init__(self, status_code=200, text="", json_body=None):
        self.status_code = status_code
        if json_body is not None:
            import json as _json
            self.text = _json.dumps(json_body)
        else:
            self.text = text

    def json(self):
        import json as _json
        return _json.loads(self.text)


@pytest.fixture
def fake_response():
    return FakeResponse


@pytest.fixture
def http(monkeypatch):
    """Patch requests.get/post on a target module with canned responses.

    Usage:
        http(module, get=FakeResponse(200, ...), post=FakeResponse(200, ...))
    or pass a callable to inspect the args.
    """
    def _patch(module, get=None, post=None):
        if get is not None:
            monkeypatch.setattr(module.requests, "get",
                                get if callable(get) else (lambda *a, **k: get))
        if post is not None:
            monkeypatch.setattr(module.requests, "post",
                                post if callable(post) else (lambda *a, **k: post))
    return _patch
