"""writ_me tests, mocked gate, no network."""

import json

from writ_mcp import server


ME_PAYLOAD = {
    "tenant": {
        "id": "ten_3fa8b91c2d44",
        "name": "Acme support",
    },
    "key": {
        "email": "ops@example.com",
        "plan": "free",
    },
    "policy": {
        "refund": "step_up",
        "verify": "require_grant",
    },
    "monthlyChecks": 10000,
}


class _KeyRecorder:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload if payload is not None else ME_PAYLOAD

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.payload


def _raise_401(method, path, body=None):
    raise server.WritError(401, {"error": "API key required."})


def _loads(s):
    return json.loads(s)


def test_me_gets_v1_me(monkeypatch):
    rec = _KeyRecorder()
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_me())
    assert out == ME_PAYLOAD
    assert rec.calls == [("GET", "/v1/me", None)]


def test_me_gate_payload_returned_verbatim(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _KeyRecorder())
    parsed = _loads(server.writ_me())
    assert parsed == ME_PAYLOAD
    assert parsed["tenant"]["id"] == "ten_3fa8b91c2d44"
    assert parsed["tenant"]["name"] == "Acme support"
    assert parsed["key"]["email"] == "ops@example.com"
    assert parsed["key"]["plan"] == "free"
    assert parsed["policy"] == {"refund": "step_up", "verify": "require_grant"}
    assert parsed["monthlyChecks"] == 10000


def test_me_writ_error_surfaces_as_standard_error_json(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _raise_401)
    out = _loads(server.writ_me())
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]
    assert out["detail"] == {"error": "API key required."}
