---
description: Run one Writ policy check for a described consequential action and explain its decision and receipt.
allowed-tools: AskUserQuestion, mcp__plugin_writ_writ__writ_check, mcp__plugin_writ_writ__writ_sandbox
argument-hint: "[sponsor, agent, verb, target, and purpose for the action]"
---

# Check one action with Writ

Use `$ARGUMENTS` and the conversation to understand the one proposed action. Collect all five required inputs before calling `writ_check`:

- `sponsor_id`: the accountable human sponsor, such as a user id or email.
- `agent_id`: the agent or workflow requesting the action.
- `verb`: the action in the tenant's verb vocabulary, such as `payments.refund`.
- `target`: the exact resource or recipient the action affects.
- `purpose`: the specific reason for this action. The authorization is bound to this purpose.

Ask the user for every missing or ambiguous input. Do not invent a sponsor, target, purpose, or tenant-specific verb. Restate the resolved inputs so the user can correct a mismatch. An optional policy environment may be supplied only if the user requested it.

Call the plugin's `writ` MCP server tool `writ_check` once with those inputs. Do not perform the consequential action as part of this command.

Interpret the returned result as follows:

- **ALLOW**: the action is authorized. Show the decision, `authToken`, expiry, and `receiptId` when returned. The token is valid for 90 seconds and is bound to the exact write. Immediately before the eventual execution, call `writ_verify_token` with that token and the exact same `verb`, `target`, and `purpose`. Execute only if verification is valid. If any field changes, or the token expires or fails verification, stop and run `writ_check` again.
- **DENY**: the action must not happen. State the decision and the returned reason. Do not retry with altered inputs to evade policy and do not call the write tool.
- **STEP_UP**: stop and surface the action and its five inputs to the human sponsor. A sponsor can approve through `writ_grant` or the dashboard. Only after that approval may the action be checked again with `writ_check`; do not treat STEP_UP as permission to execute.

Every ALLOW, DENY, or STEP_UP decision creates a receipt in Writ's hash-chained audit log. Summarize the returned `receiptId` and relevant reason or policy details without exposing any credential. A receipt is evidence of the decision, not a substitute for token verification after ALLOW.

If `WRIT_API_KEY` is not configured, tell the user to get a key at https://app.withwrit.com and export it before starting Claude Code. For a keyless demonstration only, `writ_sandbox` can issue a 90-second demo grant for `demo_write` on a target beginning with `demo-`; it is not authorization for a real write. No key or no network means no ALLOW. Never convert an MCP error, missing key, timeout, or unreachable service into permission to proceed.
