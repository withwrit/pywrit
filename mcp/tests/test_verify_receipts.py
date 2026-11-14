"""writ_verify_receipts tests — mocked gate, no network."""

import json

from writ_mcp import server


VERIFY_PAYLOAD = {
    "ok": True,
    "checked": 200,
    "tip": "9f2cdeadbeef",
    "tipReceipt": "rcpt_9d2f",
    "chainedFrom": "rcpt_51ab",
    "legacyCount": 0,
    "complete": True,
}


class _Recorder:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload if payload is not None else VERIFY_PAYLOAD

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.payload


def _raise_401(method, path, body=None):
    raise server.WritError(401, {"error": "API key required."})


def _loads(s):
    return json.loads(s)


def test_default_limit_is_200(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_verify_receipts())
    assert out == VERIFY_PAYLOAD
    assert rec.calls == [("GET", "/v1/receipts/verify?limit=200", None)]


def test_limit_zero_clamps_to_1(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_verify_receipts(limit=0))
    assert rec.calls == [("GET", "/v1/receipts/verify?limit=1", None)]


def test_limit_5000_clamps_to_1000(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_verify_receipts(limit=5000))
    assert rec.calls == [("GET", "/v1/receipts/verify?limit=1000", None)]


def test_gate_payload_returned_verbatim(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    assert _loads(server.writ_verify_receipts(limit=42)) == VERIFY_PAYLOAD


def test_writ_error_surfaces_as_standard_error_json(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _raise_401)
    out = _loads(server.writ_verify_receipts())
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]
    assert out["detail"] == {"error": "API key required."}
