# Writ for Claude Code

Writ is a policy gate and audit log for AI agent writes. Before a consequential write, the agent asks Writ with a sponsor, agent, verb, target, and purpose. Writ returns `ALLOW`, `DENY`, or `STEP_UP`, and every decision becomes a receipt in a hash-chained audit log.

This plugin gives Claude Code the Writ MCP server, an enforce-before-write skill, and commands for checking one action and scanning a repository.

## Requirements

- Claude Code.
- `uvx` on `PATH`, supplied by [uv](https://docs.astral.sh/uv/), to run the `writ-mcp` pip package on demand.
- A Writ API key for tenant policy decisions. Sign in at [app.withwrit.com](https://app.withwrit.com) to get a key.
- Python and pip only when using the scanner command and `writ` is not already installed.

Export the key in the shell before starting Claude Code:

```bash
export WRIT_API_KEY="writ_..."
claude
```

The plugin's `.mcp.json` passes `${WRIT_API_KEY}` from this environment to the MCP server. It does not store a key in the repository.

## Install

The repository root contains the `writ` marketplace and this plugin. In a Claude Code session, run:

```text
/plugin marketplace add withwrit/pywrit
/plugin install writ@writ
```

Review the plugin details, choose an install scope, and confirm the installation. The first command registers the marketplace; the second opens the plugin's installation flow as documented by Claude Code.

To install from a local checkout instead, use the absolute path to the repository root:

```text
/plugin marketplace add /absolute/path/to/writ
/plugin install writ@writ
```

Then run `/reload-plugins` if the installation summary says a reload is needed. Confirm that `/writ:scan`, `/writ:check`, and the Writ MCP tools are available. The MCP server connects to the hosted Writ API at https://api.withwrit.com.

## What is included

### Writ MCP server

`.mcp.json` declares one server named `writ` and runs `uvx writ-mcp`. The `writ-mcp` package provides 20 tools for checks, token verification, gated-execution leases and upstream execution, grants, revocation, receipts, audit-log hash-chain verification with `writ_verify_receipts`, policy, the keyless sandbox, GitHub App controls, manifests, receipt explanations, notifications, principals, verbs, and API key metadata. The main write flow uses `writ_check` and then `writ_verify_token` immediately before an allowed action.

The server needs `WRIT_API_KEY` for tenant policy checks. No key or no network means no `ALLOW`; do not treat a timeout or tool error as authorization. `writ_sandbox` is available without a key for a 90-second demonstration using `demo_write` and a target beginning with `demo-`, not for real-world authorization.

### Enforce-before-write skill

`skills/writ/SKILL.md` teaches the standing rule to call `writ_check` before money movement, messages, access or identity changes, deletes, and external API calls that act in the world. It requires the agent to honor `DENY`, surface `STEP_UP` to a human sponsor, and verify an `ALLOW` token immediately before executing. It also records scanner coverage and the fail-closed rule.

### `/writ:scan`

`commands/scan.md` installs `pywrit` with pip when `writ` is missing, runs `writ scan` on the selected repository, and summarizes discovered write sites and ungated sites by risk. It identifies coverage gaps and explains the next step: review `writ-policy.json`, then run `writ scan --apply` only after that review. The command itself does not apply instrumentation.

Coverage is Python scan plus auto-instrumentation, TypeScript and JavaScript scan-only, and Go scan-only with the first detection family. TypeScript, JavaScript, and Go scanning uses the optional `pywrit[polyglot]` dependencies.

### `/writ:check`

`commands/check.md` asks for any missing sponsor, agent, verb, target, or purpose, then runs one `writ_check` for the described action. It explains `ALLOW`, `DENY`, and `STEP_UP`, the audit log receipt, and the token verification needed before eventual execution after `ALLOW`. It does not perform the action.

## Development

The plugin manifest is `.claude-plugin/plugin.json`. The repository-level catalog is `../../.claude-plugin/marketplace.json` relative to this directory. From the repository root, validate both with:

```bash
claude plugin validate ./plugins/writ
claude plugin validate .
```
