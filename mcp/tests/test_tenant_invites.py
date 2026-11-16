"""writ_tenant_invite and writ_join_tenant tests, mocked gate, no network."""

import json

from writ_mcp import server


INVITE_PAYLOAD = {
    "inviteCode": "writ_inv_9dKx2mQvR4tY7wZ1aB3cD5e",
    "tenantId": "ten_3fa8b91c2d44",
    "note": (
        "Share this code with teammates; they pass it as inviteCode to "
        "POST /v1/keys to join this tenant. Creating a new code rotates the old one."
    ),
}

JOIN_PAYLOAD = {
    "apiKey": "writ_7hK2xQ9mZp4vT8rL3nB6cM1wJ5dG0aF2sP9yH4kU7i",
    "tenantId": "ten_3fa8b91c2d44",
    "plan": "free",
    "monthlyChecks": 10000,
    "email": "teammate@example.com",
    "principalId": "prn_9d2f4a1b2c3d",
    "defaultPolicy": {
        "verify": "require_grant",
        "verify_human": "require_grant",
        "refund": "require_grant",
        "provision": "require_grant",
        "admit": "require_grant",
        "prescribe": "require_grant",
    },
}

INVITE_CODE = "writ_inv_9dKx2mQvR4tY7wZ1aB3cD5e"


class _KeyRecorder:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload if payload is not None else INVITE_PAYLOAD

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.payload


class _CallRecorder:
    """Records the exact positional args and kwargs: the join call must pass
    no credential argument, because POST /v1/keys is unauthenticated."""

    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload if payload is not None else JOIN_PAYLOAD

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.payload


def _raise_401(method, path, body=None):
    raise server.WritError(401, {"error": "API key required."})


def _raise_400(*args, **kwargs):
    raise server.WritError(400, {"error": "Invalid or expired invite code."})


def _loads(s):
    return json.loads(s)


def test_invite_posts_to_tenant_invites_with_none_body(monkeypatch):
    rec = _KeyRecorder()
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_tenant_invite())
    assert out == INVITE_PAYLOAD
    assert rec.calls == [("POST", "/v1/tenant/invites", None)]


def test_invite_gate_payload_returned_verbatim(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _KeyRecorder())
    assert _loads(server.writ_tenant_invite()) == INVITE_PAYLOAD


def test_invite_writ_error_surfaces_as_standard_error_json(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _raise_401)
    out = _loads(server.writ_tenant_invite())
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]
    assert out["detail"] == {"error": "API key required."}


def test_join_posts_exactly_email_and_invite_code_with_no_credential(monkeypatch):
    rec = _CallRecorder()
    monkeypatch.setattr(server, "_call", rec)
    out = _loads(server.writ_join_tenant(
        email="teammate@example.com", invite_code=INVITE_CODE))
    assert out == JOIN_PAYLOAD
    assert rec.calls == [(("POST", "/v1/keys",
                           {"email": "teammate@example.com",
                            "inviteCode": INVITE_CODE}), {})]


def test_join_tenant_name_included_only_when_given(monkeypatch):
    rec = _CallRecorder()
    monkeypatch.setattr(server, "_call", rec)
    _loads(server.writ_join_tenant(
        email="teammate@example.com", invite_code=INVITE_CODE,
        tenant_name="Acme support"))
    assert rec.calls == [(("POST", "/v1/keys",
                           {"email": "teammate@example.com",
                            "inviteCode": INVITE_CODE,
                            "tenantName": "Acme support"}), {})]


def test_join_empty_tenant_name_is_not_sent(monkeypatch):
    rec = _CallRecorder()
    monkeypatch.setattr(server, "_call", rec)
    _loads(server.writ_join_tenant(
        email="teammate@example.com", invite_code=INVITE_CODE,
        tenant_name=""))
    assert rec.calls == [(("POST", "/v1/keys",
                           {"email": "teammate@example.com",
                            "inviteCode": INVITE_CODE}), {})]


def test_join_gate_payload_returned_verbatim(monkeypatch):
    monkeypatch.setattr(server, "_call", _CallRecorder())
    out = _loads(server.writ_join_tenant(
        email="teammate@example.com", invite_code=INVITE_CODE))
    assert out == JOIN_PAYLOAD


def test_join_writ_error_surfaces_as_standard_error_json(monkeypatch):
    monkeypatch.setattr(server, "_call", _raise_400)
    out = _loads(server.writ_join_tenant(
        email="teammate@example.com", invite_code=INVITE_CODE))
    assert out["status"] == 400
    assert "Writ API error 400" in out["error"]
    assert out["detail"] == {"error": "Invalid or expired invite code."}
