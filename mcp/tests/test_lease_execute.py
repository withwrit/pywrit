"""writ_lease / writ_execute request-shape tests — mocked gate, no network."""

import json

from writ_mcp import server


class _Recorder:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload if payload is not None else {"ok": True}

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.payload


def _loads(s):
    return json.loads(s)


def test_lease_full_args(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_lease("tok1", "stripe", "POST", "/v1/refunds",
                                   {"charge": "ch_1"}, 60))
    assert out == {"ok": True}
    assert rec.calls == [("POST", "/v1/leases", {
        "token": "tok1", "systemId": "stripe", "method": "POST",
        "path": "/v1/refunds", "body": {"charge": "ch_1"}, "ttlSeconds": 60,
    })]


def test_lease_minimal_omits_optional(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_lease("tok1", "github", "POST", "/repos/a/b"))
    assert rec.calls == [("POST", "/v1/leases", {
        "token": "tok1", "systemId": "github", "method": "POST", "path": "/repos/a/b",
    })]


def test_execute_with_lease(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_execute(lease_id="lease_1", system_id="stripe",
                               method="POST", path="/v1/refunds",
                               body={"charge": "ch_1"}, idempotency_key="k1"))
    assert rec.calls == [("POST", "/v1/execute", {
        "systemId": "stripe", "method": "POST", "path": "/v1/refunds",
        "leaseId": "lease_1", "body": {"charge": "ch_1"}, "idempotencyKey": "k1",
    })]


def test_execute_with_token_defaults_system(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_execute(auth_token="tok1", method="POST", path="/v1/refunds"))
    assert rec.calls == [("POST", "/v1/execute", {
        "systemId": "stripe", "method": "POST", "path": "/v1/refunds", "token": "tok1",
    })]


def test_execute_requires_exactly_one_credential(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    for kwargs in ({}, {"lease_id": "l", "auth_token": "t"}):
        out = _loads(server.writ_execute(method="POST", path="/v1/refunds", **kwargs))
        assert "error" in out
    assert rec.calls == []


def test_fail_closed_response_passes_through(monkeypatch):
    rec = _Recorder({"ok": False, "reason": "no active credential for system 'stripe'"})
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_lease("tok1", "stripe", "POST", "/v1/refunds"))
    assert out == {"ok": False, "reason": "no active credential for system 'stripe'"}
