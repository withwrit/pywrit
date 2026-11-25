"""Policy override tools tests, mocked gate, no network."""

import json

from writ_mcp import server


POLICIES_PAYLOAD = {
    "tenantId": "ten_3fa8b91c2d44",
    "environments": ["dev", "staging", "prod"],
    "policies": [
        {
            "policyId": "pol_ten_3fa8b91c2d44_tenant",
            "tenantId": "ten_3fa8b91c2d44",
            "scope": "tenant",
            "environment": None,
            "version": 3,
            "updatedAt": 1759000000,
            "policy": {"verify": "require_grant", "refund": "step_up"},
        },
        {
            "policyId": "pol_ten_3fa8b91c2d44_env_dev",
            "tenantId": "ten_3fa8b91c2d44",
            "scope": "environment",
            "environment": "dev",
            "version": 1,
            "updatedAt": 1759000100,
            "policy": {"refund": "allow"},
        },
        {
            "policyId": "pol_ten_3fa8b91c2d44_prn_prn_9d2f4a1b2c3d",
            "tenantId": "ten_3fa8b91c2d44",
            "scope": "principal",
            "environment": None,
            "principalId": "prn_9d2f4a1b2c3d",
            "principalName": "billing",
            "version": 2,
            "updatedAt": 1759000200,
            "policy": {"refund": "step_up"},
        },
    ],
}

ENV_PAYLOAD = {
    "policyId": "pol_ten_3fa8b91c2d44_env_dev",
    "tenantId": "ten_3fa8b91c2d44",
    "scope": "environment",
    "environment": "dev",
    "version": 1,
    "updatedAt": 1759000100,
    "policy": {"refund": "allow"},
    "effectivePolicy": {
        "verify": "require_grant",
        "verify_human": "require_grant",
        "refund": "allow",
        "provision": "require_grant",
        "admit": "require_grant",
        "prescribe": "require_grant",
    },
    "policyProvenance": {
        "refund": "environment",
        "verify": "tenant",
        "verify_human": "tenant",
        "provision": "tenant",
        "admit": "tenant",
        "prescribe": "tenant",
    },
}

PRINCIPAL_PAYLOAD = {
    "policyId": "pol_ten_3fa8b91c2d44_prn_prn_9d2f4a1b2c3d",
    "tenantId": "ten_3fa8b91c2d44",
    "scope": "principal",
    "environment": None,
    "principalId": "prn_9d2f4a1b2c3d",
    "principalName": "billing",
    "version": 3,
    "updatedAt": 1759000300,
    "policy": {"refund": "step_up"},
    "effectivePolicy": {
        "verify": "require_grant",
        "verify_human": "require_grant",
        "refund": "step_up",
        "provision": "require_grant",
        "admit": "require_grant",
        "prescribe": "require_grant",
    },
    "policyProvenance": {
        "refund": "principal",
        "verify": "tenant",
        "verify_human": "tenant",
        "provision": "tenant",
        "admit": "tenant",
        "prescribe": "tenant",
    },
}


class _KeyRecorder:
    def __init__(self, payload=None, error=None):
        self.calls = []
        self.payload = payload
        self.error = error

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if self.error is not None:
            raise self.error
        return self.payload


def _loads(s):
    return json.loads(s)


def test_policies_gets_v1_policies(monkeypatch):
    rec = _KeyRecorder(POLICIES_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policies())
    assert out == POLICIES_PAYLOAD
    assert rec.calls == [("GET", "/v1/policies", None)]
    scopes = [p["scope"] for p in out["policies"]]
    assert scopes == ["tenant", "environment", "principal"]


def test_policies_error_surfaces_as_standard_error_json(monkeypatch):
    rec = _KeyRecorder(error=server.WritError(401, {"error": "API key required."}))
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policies())
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]
    assert out["detail"] == {"error": "API key required."}


def test_policy_env_get_when_policy_empty(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="dev"))
    assert out == ENV_PAYLOAD
    assert rec.calls == [("GET", "/v1/policies/environments/dev", None)]
    assert out["policy"] == {"refund": "allow"}
    assert out["effectivePolicy"]["refund"] == "allow"
    assert out["policyProvenance"]["refund"] == "environment"


def test_policy_env_put_sends_bare_dict(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="staging", policy='{"refund": "allow"}'))
    assert out == ENV_PAYLOAD
    assert rec.calls == [("PUT", "/v1/policies/environments/staging", {"refund": "allow"})]


def test_policy_env_bad_environment_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="prod2"))
    assert rec.calls == []
    assert out["status"] == 400
    assert "dev, staging, or prod" in out["error"]


def test_policy_env_bad_json_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="dev", policy="{not json"))
    assert rec.calls == []
    assert out["status"] == 400
    assert "not valid JSON" in out["error"]


def test_policy_env_unknown_verb_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="dev", policy='{"fly": "allow"}'))
    assert rec.calls == []
    assert out["status"] == 400
    assert "unknown verb" in out["error"]


def test_policy_env_unknown_mode_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="dev", policy='{"refund": "maybe"}'))
    assert rec.calls == []
    assert out["status"] == 400
    assert "unknown mode" in out["error"]
    assert "allow, deny, require_grant, step_up" in out["error"]


def test_policy_env_inherit_rejected(monkeypatch):
    rec = _KeyRecorder(ENV_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="dev", policy='{"refund": "inherit"}'))
    assert rec.calls == []
    assert out["status"] == 400
    assert "unknown mode" in out["error"]


def test_policy_env_error_surfaces_as_standard_error_json(monkeypatch):
    rec = _KeyRecorder(error=server.WritError(401, {"error": "API key required."}))
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_env(environment="dev"))
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]


def test_policy_principal_get_when_policy_empty(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d"))
    assert out == PRINCIPAL_PAYLOAD
    assert rec.calls == [("GET", "/v1/policies/principals/prn_9d2f4a1b2c3d", None)]


def test_policy_principal_get_with_environment_appends_query(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", environment="prod"))
    assert rec.calls == [("GET", "/v1/policies/principals/prn_9d2f4a1b2c3d?environment=prod", None)]


def test_policy_principal_get_payload_returned_verbatim(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d"))
    assert out["policy"] == {"refund": "step_up"}
    assert out["effectivePolicy"]["refund"] == "step_up"
    assert out["policyProvenance"]["refund"] == "principal"


def test_policy_principal_tombstoned_reads_inert(monkeypatch):
    inert = dict(PRINCIPAL_PAYLOAD, inert=True)
    rec = _KeyRecorder(inert)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d"))
    assert out["inert"] is True
    assert out["policy"] == {"refund": "step_up"}


def test_policy_principal_put_sends_bare_dict(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", policy='{"refund": "step_up"}'))
    assert out == PRINCIPAL_PAYLOAD
    assert rec.calls == [("PUT", "/v1/policies/principals/prn_9d2f4a1b2c3d", {"refund": "step_up"})]


def test_policy_principal_inherit_accepted(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", policy='{"refund": "inherit"}'))
    assert rec.calls == [("PUT", "/v1/policies/principals/prn_9d2f4a1b2c3d", {"refund": "inherit"})]


def test_policy_principal_bad_environment_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", environment="qa"))
    assert rec.calls == []
    assert out["status"] == 400
    assert "dev, staging, or prod" in out["error"]


def test_policy_principal_bad_json_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", policy="[1, 2]"))
    assert rec.calls == []
    assert out["status"] == 400
    assert "JSON object" in out["error"]


def test_policy_principal_unknown_verb_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", policy='{"fly": "allow"}'))
    assert rec.calls == []
    assert out["status"] == 400
    assert "unknown verb" in out["error"]


def test_policy_principal_unknown_mode_never_calls_gate(monkeypatch):
    rec = _KeyRecorder(PRINCIPAL_PAYLOAD)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", policy='{"refund": "maybe"}'))
    assert rec.calls == []
    assert out["status"] == 400
    assert "unknown mode" in out["error"]


def test_policy_principal_inactive_surfaces_as_error_json(monkeypatch):
    err = server.WritError(400, {
        "error": "principal_inactive",
        "message": "cannot set policy for a disabled principal",
    })
    rec = _KeyRecorder(error=err)
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d", policy='{"refund": "allow"}'))
    assert out["status"] == 400
    assert out["detail"]["error"] == "principal_inactive"


def test_policy_principal_404_surfaces_as_error_json(monkeypatch):
    rec = _KeyRecorder(error=server.WritError(404, {"error": "principal not found"}))
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_not_here"))
    assert out["status"] == 404
    assert "Writ API error 404" in out["error"]
    assert out["detail"] == {"error": "principal not found"}


def test_policy_principal_error_surfaces_as_standard_error_json(monkeypatch):
    rec = _KeyRecorder(error=server.WritError(401, {"error": "API key required."}))
    monkeypatch.setattr(server, "_key_call", rec)
    out = _loads(server.writ_policy_principal(principal_id="prn_9d2f4a1b2c3d"))
    assert out["status"] == 401
    assert "Writ API error 401" in out["error"]
