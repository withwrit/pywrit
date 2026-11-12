# Writ for Cursor

Writ is a policy gate and audit log for AI agent writes. This Cursor Plugin
packages the Writ MCP server and a rule that tells the agent to check before a
consequential write. Writ returns `ALLOW`, `DENY`, or `STEP_UP`, and every
decision creates a receipt in a hash-chained audit log. The server exposes 17
tools for checks, authorization, receipts, policy, and administration.

The included scanner workflow finds write call sites in a repository. Python
supports scanning and automatic instrumentation. TypeScript and JavaScript are
scan-only. Go is scan-only with a first detection family.

## Requirements

- Cursor with local plugin imports enabled. Organization administrators may
  control local imports.
- [`uv`](https://docs.astral.sh/uv/), which supplies the `uvx` command.
  Cursor runs `uvx writ-mcp` to start the server and downloads the package on
  demand.
- A Writ API key. Sign up or sign in at
  [app.withwrit.com](https://app.withwrit.com), open **API keys**, and select
  **Create key**. Writ shows the new key once. Do not commit it to a
  repository.

The `writ-mcp` server communicates with the hosted Writ API at
`https://api.withwrit.com`. It reads the key from the public `WRIT_API_KEY`
environment variable. The plugin declares a variable with that name and passes
it to the server. The key is required for normal checks; `writ_sandbox` is the
no-key demo path and cannot authorize a real write.

## Install locally

From a checkout of this repository, copy the entire package, including its
hidden `.cursor-plugin` directory, into Cursor's local plugin directory:

```bash
mkdir -p ~/.cursor/plugins/local/writ
cp -R plugins/cursor/. ~/.cursor/plugins/local/writ/
```

1. Restart Cursor, or run **Developer: Reload Window**.
2. Open **Customize** and confirm that Writ's MCP server and rule appear.
3. Open Writ's **Configure** settings and set `WRIT_API_KEY` to the key from
   app.withwrit.com. In a team-managed deployment, an administrator sets the
   plugin variable in the Cursor dashboard under **Plugins**. Do not paste the
   key into a package file.
4. Enable the Writ MCP server and the Writ rule if they are not already
   enabled. The rule uses agent-selected application with `alwaysApply:
   false`; invoke it explicitly with `@writ` when needed.

The MCP server appears to Cursor with a plugin-specific name prefix. Its tool
names remain `writ_check`, `writ_verify_token`, and the other names listed
below. Use a sandbox check to try the workflow without a key; treat any tool,
key, or network failure during a proposed real write as a stop, not an allow.

## Use in a team

Cursor Plugins can also be distributed through team marketplaces. An
administrator can include this package in a marketplace repository using
Cursor's documented marketplace manifest format, then import that repository
through **Plugins & MCPs**. Developers then install Writ through
**Customize**, and an administrator supplies `WRIT_API_KEY` through Plugins
configuration.

This package is not submitted to the public Cursor Marketplace by this
repository. Local installation does not require marketplace publication.

## What the rule teaches

Before moving money, sending a message, changing access or identity, deleting
data, or calling an external API that acts in the world, the agent must:

1. Call `writ_check` with the sponsor, agent, verb, target, and purpose.
2. Stop on `DENY`.
3. Pause on `STEP_UP` and surface the action for human approval. After a
   sponsor approves it with `writ_grant` or the dashboard, check again.
4. On `ALLOW`, call `writ_verify_token` immediately before executing the exact
   write authorized by the returned token.
5. For a write to a vaulted upstream system (`stripe`, `github`, `salesforce`),
   convert the ALLOW token with `writ_lease`, then run it with `writ_execute`
   using the same method, path, and body. A lease is single-use and bound to
   that exact request; on any mismatch the gate fails closed with no upstream call.
6. Fail closed if no key is configured or Writ cannot be reached. Use
   `writ_sandbox` only for a no-key demo, never as authorization for a real
   action.

Every confirmed decision has a receipt in the audit log. The rule also teaches
this scanner workflow:

```bash
pip install pywrit
writ scan .
```

The scan reports likely write sites, writes `writ-policy.json`, and previews
suggested instrumentation. Review the policy file and diff, check the proposed
verbs and purposes, then run and confirm:

```bash
writ scan . --apply
```

Review the resulting changes. Python files can be instrumented automatically.
For local TypeScript, JavaScript, and Go parsing, install the optional parser
dependencies with `pip install 'pywrit[polyglot]'`. These language files are
never rewritten by `--apply`; gate those findings manually. The scanner does
not provide complete security coverage and can miss write sites. See the
[scanner documentation](https://docs.withwrit.com/scanner) for detected
patterns and coverage limitations.

## Writ MCP tools

The server exposes 19 tools:

| Area | Tools |
| --- | --- |
| Check and verify | `writ_check`, `writ_verify_token` |
| Gated execution | `writ_lease`, `writ_execute` |
| Sponsor controls | `writ_grant`, `writ_revoke`, `writ_reinstate` |
| Receipts and policy | `writ_receipts`, `writ_policy`, `writ_explain_receipt` |
| Demo | `writ_sandbox` |
| GitHub App | `writ_github_installations`, `writ_github_set_threshold`, `writ_github_toggle_pr_comments` |
| Repository manifests | `writ_manifests` |
| Tenant settings | `writ_tenant_notify` |
| Principals and verbs | `writ_principals`, `writ_verbs` |
| Keys | `writ_keys` |

Sponsor operations require separate sponsor authorization. The Writ dashboard
and the [MCP server documentation](https://docs.withwrit.com/mcp) provide the
administrative setup. Agents do not need the sponsor credential for the normal
check and verify loop or the sandbox.

## Package layout

```text
.cursor-plugin/plugin.json  Cursor Plugin manifest and API key variable
mcp.json                   Writ stdio MCP server, started with uvx
rules/writ.mdc             Check-before-write and scanner guidance
README.md                  Installation and usage
```

The package follows Cursor's documented Cursor Plugin format. Component paths
are explicit in the manifest and also match Cursor's default discovery
locations. References:

- [Plugins](https://cursor.com/docs/plugins)
- [Plugins reference](https://cursor.com/docs/reference/plugins)
- [Rules](https://cursor.com/docs/rules)
- [MCP servers](https://cursor.com/docs/mcp)
