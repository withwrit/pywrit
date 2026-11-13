"""writ-mcp package tests — import-time checks only, no network."""

import asyncio

import writ_mcp
from writ_mcp import server

EXPECTED_TOOLS = {
    "writ_check",
    "writ_verify_token",
    "writ_lease",
    "writ_execute",
    "writ_grant",
    "writ_revoke",
    "writ_reinstate",
    "writ_receipts",
    "writ_policy",
    "writ_sandbox",
    "writ_github_installations",
    "writ_github_set_threshold",
    "writ_github_toggle_pr_comments",
    "writ_manifests",
    "writ_explain_receipt",
    "writ_tenant_notify",
    "writ_principals",
    "writ_verbs",
    "writ_keys",
}


def test_version():
    assert writ_mcp.__version__ == "0.2.2"


def test_public_base_url_default():
    # The public package must never default to an internal endpoint.
    assert server.BASE_URL == "https://api.withwrit.com"
    assert "lambda-url" not in server.BASE_URL


def test_all_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS


def test_main_entrypoint_exists():
    assert callable(server.main)
