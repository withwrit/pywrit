"""writ_badge_token and writ_badge_revoke tests, mocked gate, no network."""

import json

from writ_mcp import server


BADGE_MINT_PAYLOAD = {
    "badgeToken": "writ_badge_9dKx2mQvR4tY7wZ1aB3cD5eF6gH8jK0lMn",
    "badgeUrl": "https://api.withwrit.com/v1/badge/writ_badge_9dKx2mQvR4tY7wZ1aB3cD5eF6gH8jK0lMn.svg",
    "markdown": "[![agent writes gated by Writ](https://api.withwrit.com/v1/badge/writ_badge_9dKx2mQvR4tY7wZ1aB3cD5eF6gH8jK0lMn.svg)](https://withwrit.com)",
    "label": "support-agent repo",
    "note": "The badge token is public by design: it lives in your README. It cannot be used as an API key. Store it: it is shown once and is required to revoke the badge.",
}

TOKEN = "writ_badge_9dKx2mQvR4tY7wZ1aB3cD5eF6gH8jK0lMn"


class _Recorder:
    def __init__(self, payload=None):
        self.calls = []
        self.payload = payload if payload is not None else BADGE_MINT_PAYLOAD

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        return self.payload


def _raise_401(method, path, body=None):
    raise server.WritError(401, {"error": "API key required."})


def _raise_404(method, path, body=None):
    raise server.WritError(404, {"error": "unknown badge token"})


def _loads(s):
    return json.loads(s)


def test_mint_with_no_label_posts_none_body(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_badge_token())
    assert out == BADGE_MINT_PAYLOAD
    assert rec.calls == [("POST", "/v1/badge/tokens", None)]


def test_mint_with_label_passes_label_body(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_badge_token(label="support-agent repo"))
    assert rec.calls == [("POST", "/v1/badge/tokens", {"label": "support-agent repo"})]


def test_gate_payload_returned_verbatim(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(server, "_key_call", rec)
    assert _loads(server.writ_badge_token()) == BADGE_MINT_PAYLOAD


def test_mint_writ_error_surfaces_as_standard_error_json(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _raise_401)
    out = _loads(server.writ_badge_token())
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]
    assert out["detail"] == {"error": "API key required."}


def test_revoke_posts_badge_token_body(monkeypatch):
    rec = _Recorder({"revoked": True})
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_badge_revoke(badge_token=TOKEN))
    assert out == {"revoked": True}
    assert rec.calls == [("POST", "/v1/badge/tokens/revoke", {"badgeToken": TOKEN})]


def test_revoke_writ_error_surfaces_as_standard_error_json(monkeypatch):
    monkeypatch.setattr(server, "_key_call", _raise_404)
    out = _loads(server.writ_badge_revoke(badge_token=TOKEN))
    assert out["status"] == 404
    assert "Writ API error 404" in out["error"]
    assert out["detail"] == {"error": "unknown badge token"}
