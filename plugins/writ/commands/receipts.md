---
description: List recent Writ decision receipts, explain one receipt by id, or verify the audit-log hash chain.
allowed-tools: mcp__plugin_writ_writ__writ_receipts, mcp__plugin_writ_writ__writ_explain_receipt, mcp__plugin_writ_writ__writ_verify_receipts
argument-hint: "[empty for the 10 latest receipts, a count 1-50, a receipt id, or verify]"
---

# Inspect Writ receipts

Read the tenant's audit log with `$ARGUMENTS` in exactly one of these forms:

- **Empty**: list the 10 most recent receipts.
- **A number N from 1 to 50**: list the N most recent receipts.
- **A receipt id**: explain that one receipt.
- **The single word `verify`**: prove the audit-log hash chain is intact.

Anything else is none of these forms. Do not guess: ask the user which of the four they meant, and wait for the answer.

## List form (empty or a number)

Call the plugin's `writ` MCP server tool `writ_receipts` once with the limit. Summarize the returned receipts as a table with one row per receipt:

- Receipt id (the short form is fine when the tool returns one).
- Decision: ALLOW, DENY, or STEP_UP.
- Verb.
- Target.
- Sponsor or agent, whichever the receipt returns.
- Time, when the receipt returns one.

Show only fields the tool actually returned; do not invent values to fill the table. When the list is empty, say plainly that no decisions have been recorded yet. An empty list is a true answer, not an error.

## Explain form (a receipt id)

Call `writ_explain_receipt` once with the given id. Summarize the decision, the five checked inputs (sponsor, agent, verb, target, purpose), and what happened next only when the explanation says so. If the tool reports the id as unknown, relay that error and stop. Do not guess a different id or retry with a reshaped one.

## Verify form (the word `verify`)

Call `writ_verify_receipts` once. Report whether the audit-log hash chain is intact, and include the count of receipts it checked. If the tool reports a break, say so plainly and name the receipt it identifies, then stop. Do not soften a broken chain or reframe it as a warning.

## Keys and failures

If `WRIT_API_KEY` is not configured, tell the user to get a key at https://app.withwrit.com and export it before starting Claude Code. A teammate joining an existing tenant can instead call `writ_join_tenant(email, invite_code)` with the team's live invite code and export the API key it returns. For a keyless demonstration only, `writ_sandbox` can issue a 90-second demo grant; a sandbox receipt is a demo record, not evidence about a real write.

No key, no network, or an MCP tool error means no receipts. Report what prevented the read, and never present a cached or guessed list. Never print an auth token; receipt ids are fine to show.

## Read-only

This command reads the audit log only. It never performs a write, never calls `writ_check`, never grants an approval, and never executes anything.
