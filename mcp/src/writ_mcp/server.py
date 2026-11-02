"""Writ MCP server — point-of-action policy checks for AI agents, as MCP tools.

An agent (or any MCP client) calls `writ_check` BEFORE performing a
consequential write. Writ answers ALLOW, DENY, or STEP_UP, and every outcome
creates an audit receipt. On ALLOW the agent also receives a 90-second
purpose-bound auth token; it must pass `writ_verify_token` against the
intended verb/target/purpose immediately before executing the write.

Configuration (environment variables):
  WRIT_BASE_URL      Gate base URL. Defaults to the hosted Writ gate
                     (https://api.withwrit.com).
  WRIT_API_KEY       API key (starts with writ_). Get one free: POST /v1/keys
                     with an email (see the Writ docs quickstart).
  WRIT_SPONSOR_TOKEN Tenant sponsor token (writ_sp_..., shown once at key
                     issuance). Only needed for sponsor tools
                     (writ_grant, writ_revoke, writ_reinstate).

Run:  writ-mcp                  (stdio transport, installed via pip)
      python -m writ_mcp.server (same, without the console script)
"""

import json
import os
import urllib.parse

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get(
    "WRIT_BASE_URL",
    "https://api.withwrit.com",
).rstrip("/")
API_KEY = os.environ.get("WRIT_API_KEY", "").strip()
SPONSOR_TOKEN = os.environ.get("WRIT_SPONSOR_TOKEN", "").strip()

mcp = FastMCP("writ")


class WritError(Exception):
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload
        super().__init__(f"Writ API error {status}: {payload}")


def _call(method, path, body=None, credential="", timeout=20.0):
    """Low-level gate call. Returns parsed JSON, raises WritError on failure."""
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}
    if credential:
        headers["Authorization"] = f"Bearer {credential}"
    with httpx.Client(timeout=timeout) as client:
        resp = client.request(method, url, headers=headers,
                              content=json.dumps(body) if body is not None else None)
    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text[:500]}
    if resp.status_code >= 400:
        raise WritError(resp.status_code, payload)
    return payload


def _key_call(method, path, body=None):
    if not API_KEY:
        raise WritError(0, {"error": "WRIT_API_KEY is not set. Get a free key: POST /v1/keys with an email."})
    return _call(method, path, body, credential=API_KEY)


def _sponsor_call(method, path, body=None):
    if not SPONSOR_TOKEN:
        raise WritError(0, {"error": "WRIT_SPONSOR_TOKEN is not set. Sponsor tools need the tenant's sponsor token."})
    return _call(method, path, body, credential=SPONSOR_TOKEN)


def _fmt(result):
    return json.dumps(result, indent=2)


@mcp.tool()
def writ_check(sponsor_id: str, agent_id: str, verb: str, target: str, purpose: str, environment: str = "") -> str:
    """Ask Writ whether an action may proceed. CALL THIS BEFORE any consequential write.

    A consequential write is anything hard to undo: sending money or messages,
    changing access or identity records, deleting data, calling an external API
    that acts in the world.

    Args:
        sponsor_id: The human sponsor accountable for this action (e.g. a user id or email).
        agent_id:   The agent or workflow performing the action.
        verb:       What is being done (e.g. "verify_human", "send_payment").
        target:     What it acts on (e.g. "benefit-case-123").
        purpose:    Why, in plain words. Be specific — the approval is bound to this purpose.
        environment: Optional policy environment: "dev", "staging", or "prod".
            The check runs against that environment's policy override (verbs it
            doesn't override inherit the tenant default). Omit for the tenant
            default. An unknown name denies fail-closed — never silently falls
            back.

    Returns a decision:
      ALLOW   — proceed. You get an authToken valid 90 seconds, bound to this
                exact sponsor/agent/verb/target/purpose. Call writ_verify_token
                against the intended write immediately before executing it.
      DENY    — do NOT perform the action. Explain the receipt reason to the user.
      STEP_UP — a human sponsor must approve first. Tell the user what needs
                approval; they can approve via writ_grant (or the dashboard),
                then call writ_check again.
    Every outcome creates an audit receipt with a receiptId.
    """
    try:
        body = {
            "sponsorId": sponsor_id, "agentId": agent_id,
            "verb": verb, "target": target, "purpose": purpose,
        }
        if environment:
            body["environment"] = environment
        return _fmt(_key_call("POST", "/v1/check", body))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_verify_token(auth_token: str, verb: str, target: str, purpose: str) -> str:
    """Verify a Writ auth token against the write you are about to execute.

    Call this IMMEDIATELY before executing an ALLOWed write, with the exact
    verb/target/purpose you intend. If valid is false — expired, tampered, or
    bound to a different purpose — do NOT execute the write; call writ_check again.

    This is the point-of-action enforcement: the check authorizes, the token proves
    the authorization still matches what you are actually doing.
    """
    try:
        return _fmt(_key_call("POST", "/v1/tokens/verify", {
            "token": auth_token, "verb": verb, "target": target, "purpose": purpose,
        }))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_grant(sponsor_id: str, agent_id: str, verb: str, target: str, purpose: str,
              ttl_seconds: int = 90) -> str:
    """SPONSOR ONLY. Mint a one-time grant approving a specific action.

    Use this when writ_check returned STEP_UP and the human sponsor approves.
    The grant is single-use: the next writ_check consumes it and returns ALLOW.
    The grant is scoped to your tenant. Requires WRIT_SPONSOR_TOKEN.
    """
    try:
        return _fmt(_sponsor_call("POST", "/v1/grants", {
            "sponsorId": sponsor_id, "agentId": agent_id,
            "verb": verb, "target": target, "purpose": purpose,
            "ttlSeconds": ttl_seconds,
        }))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_revoke(sponsor_id: str, agent_id: str) -> str:
    """SPONSOR ONLY. Kill switch: immediately deny all future checks for this principal.

    Revocation overrides live grants and tenant policy. Use when a principal is
    compromised, misbehaving, or its task is done. Scoped to your tenant.
    Requires WRIT_SPONSOR_TOKEN.
    """
    try:
        return _fmt(_sponsor_call("POST", "/v1/revoke", {
            "sponsorId": sponsor_id, "agentId": agent_id,
        }))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_reinstate(sponsor_id: str, agent_id: str) -> str:
    """SPONSOR ONLY. Undo writ_revoke: the principal is evaluated by policy again.

    Scoped to your tenant. Requires WRIT_SPONSOR_TOKEN.
    """
    try:
        return _fmt(_sponsor_call("POST", "/v1/reinstate", {
            "sponsorId": sponsor_id, "agentId": agent_id,
        }))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_receipts(limit: int = 10) -> str:
    """List recent decision receipts (audit trail). Newest first."""
    try:
        data = _key_call("GET", "/v1/receipts")
        receipts = data.get("receipts", data)
        if isinstance(receipts, list):
            receipts = receipts[: max(1, limit)]
        return _fmt(receipts)
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_policy() -> str:
    """Read the tenant's verb policy: which verbs allow, deny, require a grant, or step up."""
    try:
        return _fmt(_key_call("GET", "/v1/policy"))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_sandbox(sponsor_id: str, agent_id: str, target: str, purpose: str) -> str:
    """Get a free 90-second sandbox grant for a demo write. No API key needed.

    Issues a live grant for verb "demo_write" on a target starting with "demo-",
    then runs writ_check so you get back an ALLOW decision plus auth token to
    practice the verify-before-write flow end to end.
    """
    try:
        grant = _call("POST", "/v1/sandbox", {
            "sponsorId": sponsor_id, "agentId": agent_id,
            "verb": "demo_write", "target": target, "purpose": purpose,
        })
        return _fmt({"sandboxGrant": grant,
                     "note": 'Now call writ_check with verb "demo_write" to get your ALLOW + authToken.'})
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_github_installations() -> str:
    """List the GitHub App installations for this tenant.

    Returns each installation's id, status, PR-comment bot setting, and the
    per-installation check-run fail threshold (checkFailUngated). Use this to
    discover installation ids before calling writ_github_set_threshold or
    writ_github_toggle_pr_comments.
    """
    try:
        return _fmt(_key_call("GET", "/v1/github/installations"))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_github_set_threshold(installation_id: str, threshold: int = None) -> str:
    """Set the per-installation check-run fail threshold.

    A positive number N makes the GitHub check run fail when the ungated-site
    count is greater than N; a zero-ungated scan passes. Omit threshold (or set
    it to None) to clear the override and restore neutral-only check runs.
    """
    try:
        body = {"installationId": installation_id}
        if threshold is not None:
            body["threshold"] = threshold
        return _fmt(_key_call("POST", "/v1/github/check-fail-threshold", body))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_github_toggle_pr_comments(installation_id: str, enabled: bool) -> str:
    """Enable or disable the optional PR-comment bot for a GitHub App installation.

    Default is OFF. No TOTP step-up is required. Use writ_github_installations
    to find installation_id.
    """
    try:
        return _fmt(_key_call("POST", "/v1/github/pr-comments",
            {"installationId": installation_id, "enabled": enabled}))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_manifests(repo_id: str = "") -> str:
    """List scanned repos and their risk profiles, or fetch one manifest.

    With no repo_id, returns a table of repos with writScore, scanStatus, and
    riskDigest (counts per risk class). With repo_id, returns the full signed
    manifest for that repo.
    """
    try:
        path = "/v1/manifests"
        if repo_id:
            path += "/" + urllib.parse.quote(repo_id, safe="")
        return _fmt(_key_call("GET", path))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_explain_receipt(receipt_id: str) -> str:
    """Fetch a receipt and explain it in plain language.

    Use this to understand why a writ_check returned ALLOW, DENY, STEP_UP, or
    REVOKED. Returns the receipt with a human-readable breakdown.
    """
    try:
        return _fmt(_key_call("GET", "/v1/receipts/" + urllib.parse.quote(receipt_id, safe="")))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_tenant_notify(step_up_email: bool = None, step_up_webhook_url: str = "",
                       step_up_webhook_type: str = "") -> str:
    """Get or update step-up notification settings.

    With no arguments, returns the current settings. With arguments, updates
    them: step_up_email enables/disables step-up emails; step_up_webhook_url
    sets a generic or Slack webhook URL; use an empty string to clear.
    """
    try:
        body = {}
        if step_up_email is not None:
            body["stepUpEmail"] = step_up_email
        if step_up_webhook_url:
            body["stepUpWebhookUrl"] = step_up_webhook_url
            body["stepUpWebhookType"] = step_up_webhook_type or "generic"
        if body:
            return _fmt(_key_call("POST", "/v1/tenant/notify", body))
        return _fmt(_key_call("GET", "/v1/tenant/notify"))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_principals() -> str:
    """List the tenant's principals (identity directory)."""
    try:
        return _fmt(_key_call("GET", "/v1/principals"))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_verbs() -> str:
    """List the tenant's verb vocabulary, including custom verbs."""
    try:
        return _fmt(_key_call("GET", "/v1/verbs"))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


@mcp.tool()
def writ_keys() -> str:
    """List API key metadata for the tenant (never raw keys)."""
    try:
        return _fmt(_key_call("GET", "/v1/keys"))
    except WritError as e:
        return _fmt({"error": str(e), "status": e.status, "detail": e.payload})


def main():
    """Console-script entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
