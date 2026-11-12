---
description: Scan this repository with Writ, summarize write-site risk, and explain the review and apply steps.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: "[repository path, default: current repository]"
---

# Scan this repository with Writ

Scan only the current repository, or the single existing repository directory given in `$ARGUMENTS`. Do not scan parent directories or unrelated checkouts.

1. Determine the repository root. From that root, use `pwd` for a filesystem repository or `git rev-parse --show-toplevel` for a git checkout. If the user supplied a path, confirm it is an existing directory and use its repository root. Work from that root for the rest of this workflow.
2. Check whether the `writ` command is available with `command -v writ`. If it is missing, run exactly:

   ```bash
   python3 -m pip install pywrit
   ```

   If that Python is unavailable, use `python -m pip install pywrit`. If installation fails, report the error and stop. Do not modify repository source to work around a failed installation.
3. Run `writ scan <repository-root>`. Keep the scan read-only: do not add `--apply`, `--push-policy`, or any other publishing option. The normal scan may create `writ-policy.json`; leave its contents intact for review.
4. Summarize the actual output rather than inventing findings. Include:
   - Total write sites and gated versus ungated counts, separated by language when the report does so.
   - The overall Writ Score and the high-risk and medium counts when present.
   - The risk profile by class: money, db, auth, email, fs, network, and other. Report only classes and counts supported by the scan output.
   - The top-risk ungated sites with `path:line`, verb, risk class, and score, grouped by risk. Put money movement and destructive or privileged operations first when the risk scores support that order.
   - Any skipped files, unscanned-language warnings, suppressed findings, or scanner errors. Never equate "no findings" with "no writes exist" when coverage was incomplete.
5. Explain the next step explicitly: review the generated `writ-policy.json` and confirm the discovered verbs and policy modes. After that review, the user can run `writ scan <repository-root> --apply` to insert gates. Ask before applying changes; this scan workflow must not run `--apply` itself.

Coverage is Python scan plus auto-instrumentation, TypeScript and JavaScript scan-only, and Go scan-only with the first detection family. `--apply` does not instrument TypeScript, JavaScript, or Go. TypeScript, JavaScript, and Go scanning requires the optional polyglot support; if the output says it is missing, tell the user to run `python3 -m pip install 'pywrit[polyglot]'`, then rerun the scan. Do not claim that the base `pywrit` install scanned those languages when it did not.
