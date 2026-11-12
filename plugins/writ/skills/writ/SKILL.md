---
name: writ
description: Enforce Writ before consequential agent writes, handle ALLOW, DENY, and STEP_UP, verify authorization tokens, and understand scanner coverage. Use before money movement, messages, access or identity changes, deletes, deploys, state-changing external API calls, or other hard-to-undo actions.
allowed-tools: mcp__plugin_writ_writ__writ_check, mcp__plugin_writ_writ__writ_verify_token, mcp__plugin_writ_writ__writ_sandbox, mcp__plugin_writ_writ__writ_receipts, mcp__plugin_writ_writ__writ_explain_receipt
---

# Writ enforce-before-write rule

Writ is a policy gate and audit log for AI agent writes. Treat this as a standing rule throughout the task, not as a one-time checklist.

## Stop before a consequential write

Before any consequential write, call the `writ` MCP server's `writ_check` with the exact `sponsor_id`, `agent_id`, `verb`, `target`, and `purpose` for the proposed action. Do this after resolving the concrete target and before invoking the tool that acts.

Consequential writes include:

- Moving money, issuing refunds, changing billing, or making purchases.
- Sending email, chat messages, notifications, or other communications.
- Changing access, permissions, credentials, accounts, or identity records.
- Deleting or destructively replacing data or resources.
- Deploying, provisioning, or modifying external systems.
- Calling an external API that acts in the world or changes state.

Include other hard-to-undo actions even when they are not in this list. Local, reversible drafting is not by itself a consequential write, but publishing or committing that draft to an external system can be. Ask the user for missing sponsor, agent, verb, target, or purpose values rather than guessing them. Never skip the check because a previous action was allowed: a check and its token are bound to the exact write.

## Honor the decision

### ALLOW

ALLOW authorizes only the checked action. Keep the returned `authToken` and `receiptId` private. The token lasts 90 seconds and is bound to the exact write.

Immediately before executing the action, call `writ_verify_token` with the token and the exact intended `verb`, `target`, and `purpose`. Execute only when verification is valid and those fields still match. If verification fails, the token expires, or the action changes, do not execute. Run `writ_check` again for the action as it now stands.

### DENY

Do not perform the action, directly or through another tool. Do not retry with changed wording or inputs to evade the decision. Tell the user the action was denied and summarize the returned reason and receipt.

### STEP_UP

Do not perform the action. Stop that action and surface it to the human sponsor, including the sponsor, agent, verb, target, purpose, returned reason, and receipt id. Explain that explicit human approval is required. The sponsor can use `writ_grant` or the dashboard to approve. After approval, run `writ_check` again; only a subsequent ALLOW plus successful token verification permits execution. Never approve on the user's behalf or treat silence as approval.

Every decision lands in Writ's hash-chained audit log as a receipt. The record includes ALLOW, DENY, and STEP_UP outcomes. Use `writ_receipts` to inspect recent decisions and `writ_explain_receipt` when the user needs a receipt explained.

## Fail closed and use the sandbox honestly

No configured Writ API key or no network means no ALLOW. A missing key, an unreachable hosted API at https://api.withwrit.com, a timeout, an invalid response, or an MCP tool error is not permission to proceed. Stop the consequential write and tell the user what prevented the check or verification. Do not substitute a local guess, cached decision, or unverified token.

The MCP server requires `WRIT_API_KEY` for tenant policy checks. When no key is configured, use `writ_sandbox` only to demonstrate the flow. It issues a 90-second grant for the demo verb `demo_write` on a target beginning with `demo-`. Follow the returned instructions for the sandbox check. A sandbox result does not authorize a real-world write. Obtain a real key at https://app.withwrit.com for tenant policy decisions.

## Scanner coverage

The scanner is the pip package `pywrit`, which installs the `writ` command:

- **Python:** scan and auto-instrument with `writ scan --apply` after reviewing `writ-policy.json`.
- **TypeScript and JavaScript:** scan-only. Do not claim `--apply` instruments them.
- **Go:** scan-only with the first detection family. Do not claim complete Go detection or auto-instrumentation.

A scan is discovery, not a policy decision. Findings are heuristic and incomplete language coverage is not evidence that a repository has no consequential writes. Check the actual write immediately before execution even when a scanner did not report its call-site.

## Related workflows

Use `/writ:scan` to scan a repository and summarize risk. Use `/writ:check` to resolve the five inputs for one described action, call `writ_check`, and explain the outcome without executing the action.
