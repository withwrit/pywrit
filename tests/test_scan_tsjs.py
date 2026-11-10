#!/usr/bin/env python3
"""Deterministic tests for `writ scan` TypeScript/JavaScript support.

Fixtures live in tests/fixtures/tsjs. Every line tagged `// expect: <rule>`
must be reported with that rule, and nothing else may be reported.
Tests that parse TS/JS skip when the optional `polyglot` extra
(tree-sitter) is not installed; the rest run with zero extra deps.
"""

import argparse
import contextlib
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from pywrit import cli  # noqa: E402

FIXTURES = HERE / "fixtures" / "tsjs"
HAVE_EXTRA = bool(cli._tsjs_parsers())
_BLOCK_EXTRA = {m: None for m in ("tree_sitter", "tree_sitter_typescript",
                                  "tree_sitter_javascript",
                                  "tree_sitter_language_pack")}
_EXPECT = re.compile(r"//\s*expect:\s*([a-z0-9-]+)")
_FINDING = re.compile(
    r"^    (?P<file>\S+):(?P<line>\d+) \[(?P<kind>[a-z]+)\] "
    r"(?P<rule>[a-z0-9-]+) (?P<func>\S+)\(\): (?P<snippet>.+)$")


def _args(path, policy_out, **kw):
    ns = argparse.Namespace(path=str(path), exclude=[], policy_out=str(policy_out),
                            apply=False, yes=False, score=False, push_policy=False,
                            key="")
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def _run_scan(path, **kw):
    """Run scan_cmd in-process; return (exit code, stdout)."""
    with tempfile.TemporaryDirectory() as td:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.scan_cmd(_args(path, pathlib.Path(td) / "policy.json", **kw))
        return code, buf.getvalue()


def _expected():
    exp = set()
    for p in sorted(FIXTURES.rglob("*")):
        if p.suffix not in cli._TSJS_EXTS:
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            m = _EXPECT.search(line)
            if m:
                exp.add((str(p.relative_to(FIXTURES)), i, m.group(1)))
    return exp


def _findings(out):
    return {(m.group("file"), int(m.group("line")), m.group("rule"))
            for m in map(_FINDING.match, out.splitlines()) if m}


def _copy_fixtures(dst):
    shutil.copytree(str(FIXTURES), str(dst))
    return dst


class FixtureRulesTest(unittest.TestCase):
    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_every_expected_finding_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as td:
            root = _copy_fixtures(pathlib.Path(td) / "repo")  # outside git
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertEqual(_findings(out), _expected(), out)

    def test_every_rule_has_a_fixture(self):
        covered = {r for (_f, _l, r) in _expected()}
        self.assertEqual(covered, {r[0] for r in cli._TSJS_RULES})

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_negative_reads_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            shutil.copy(str(FIXTURES / "reads.tsx"), str(root / "reads.tsx"))
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertIn("ts/js files scanned: 1  skipped: 0", out)
        self.assertIn("ts/js write sites: 0 in 0 function(s)", out)
        self.assertEqual(_findings(out), set())
        self.assertIn("nothing to instrument.", out)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_output_format_counts_gating_and_verbs(self):
        with tempfile.TemporaryDirectory() as td:
            root = _copy_fixtures(pathlib.Path(td) / "repo")
            policy = pathlib.Path(td) / "p.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.scan_cmd(_args(root, policy))
            out = buf.getvalue()
            verbs = __import__("json").loads(policy.read_text())
        self.assertEqual(code, 0)
        n = len(_expected())
        self.assertIn("ts/js files scanned: 9  skipped: 0  (scan only, no --apply)", out)
        self.assertIn("ts/js write sites: %d in 18 function(s)" % n, out)
        self.assertIn("ts/js gated: 1/%d" % n, out)  # gated.ts calls writCheck
        self.assertIn("    payments/refunds.service.ts:10 [sdk] stripe-write "
                      "issueRefund(): stripe.refunds.create({ charge: chargeId })", out)
        self.assertIn("    http.ts:10 [http] fetch-write createOrder(): fetch(url, "
                      "{ method: \"POST\", body: JSON.stringify(body) })", out)
        for v in ("payments.refund", "payments.record", "payments.export",
                  "storage.save", "storage.create", "http.create", "legacy.write",
                  "rest.create", "rest.update", "rest.delete"):
            self.assertEqual(verbs.get(v), "require_grant", v)
        self.assertIn("nothing to instrument (ts/js findings are scan-only", out)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_apply_never_rewrites_tsjs_but_still_gates_python(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            (root / "orders").mkdir(parents=True)
            ts = root / "orders" / "api.ts"
            ts.write_text('export async function createOrder(u: string) {\n'
                          '  await fetch(u, { method: "POST" });\n}\n')
            py = root / "orders" / "store.py"
            py.write_text('def create_order():\n'
                          '    with open("/tmp/o", "w") as f:\n'
                          '        f.write("o")\n')
            before = ts.read_bytes()
            code, out = _run_scan(root, apply=True, yes=True)
            self.assertEqual(code, 0)
            self.assertEqual(ts.read_bytes(), before)
            self.assertIn("_writ_check(\"orders.create\")", py.read_text())
            self.assertIn("orders/api.ts:2 [http] fetch-write createOrder()", out)
            self.assertIn("applied 1 gate(s) to 1 file(s).", out)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_exec_kind_generic_function_does_not_crash(self):
        """Regression for KeyError: 'exec' when a child_process call is in a
        generically-named function (run/execute/handle/do) and verb inference
        falls back to the kind's default action."""
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            (root / "exec.ts").write_text(
                'import { exec } from "node:child_process";\n'
                'export function run() {\n'
                '  exec("ls");\n'
                '}\n')
            policy = pathlib.Path(td) / "policy.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.scan_cmd(_args(root, policy))
            out = buf.getvalue()
            verbs = __import__("json").loads(policy.read_text())
        self.assertEqual(code, 0)
        self.assertIn("ts/js files scanned: 1  skipped: 0", out)
        self.assertIn("[exec] child-process run()", out)
        self.assertEqual(verbs.get("exec.execute"), "require_grant")

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_exec_kind_json_mode_does_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            (root / "exec.ts").write_text(
                'import { exec } from "node:child_process";\n'
                'export function run() {\n'
                '  exec("ls");\n'
                '}\n')
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.scan_cmd(_args(root, pathlib.Path(td) / "policy.json",
                                           format="json"))
            out = buf.getvalue()
        self.assertEqual(code, 0)
        doc = __import__("json").loads(out)
        self.assertEqual(doc["findings"][0]["kind"], "exec")
        self.assertEqual(doc["findings"][0]["verb"], "exec.execute")


class FileWalkTest(unittest.TestCase):
    """File collection is stdlib-only, so these run with or without the extra."""

    WRITE = 'export function f(){ return fetch("/x", { method: "POST" }); }\n'

    def _tree(self, root, rels):
        for rel in rels:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.WRITE)

    def test_skip_dirs_and_test_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            skipped = ["node_modules/pkg/index.js", "dist/app.js", "build/app.js",
                       ".next/server/page.js", ".git/hooks/x.js",
                       "vendor/lib.js", "venv/lib/x.js", ".venv/x.js",
                       "src/__tests__/a.ts", "tests/a.ts", "src/a.test.ts",
                       "src/a.spec.tsx", "types/a.d.ts", "public/app.min.js",
                       "src/readme.md", "src/a.py"]
            kept = ["src/a.ts", "src/b.tsx", "src/c.js", "src/d.jsx",
                    "src/e.mjs", "src/f.cjs", "lib/distance.ts"]
            self._tree(root, skipped + kept)
            got = [str(p.relative_to(root))
                   for p in cli._tsjs_collect_files(root, [])]
        self.assertEqual(sorted(got), sorted(kept))

    def test_exclude_substring(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._tree(root, ["src/a.ts", "generated/b.ts"])
            got = [str(p.relative_to(root))
                   for p in cli._tsjs_collect_files(root, ["generated"])]
        self.assertEqual(got, ["src/a.ts"])

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_respects_gitignore_inside_git_repo(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("generated/\n*.gen.ts\n")
            self._tree(root, ["src/a.ts", "generated/b.ts", "src/c.gen.ts",
                              "node_modules/x/y.js"])
            got = [str(p.relative_to(root))
                   for p in cli._tsjs_collect_files(root, [])]
        self.assertEqual(got, ["src/a.ts"])


class ResourceWriteTest(unittest.TestCase):
    """Regression for generated REST resource clients (twilio-style): the
    fixture has a version request pipeline plus a resource class and a
    factory-pattern list whose create/update/patch/remove methods route
    requests with an explicit write HTTP method. Only those methods are
    findings; fetch/list/get reads (even through pipeline calls) are not."""

    EXPECTED = {
        ("rest/account.ts", 52, "resource-write"),  # update()
        ("rest/account.ts", 56, "resource-write"),  # updateWithHttpInfo()
        ("rest/account.ts", 60, "resource-write"),  # remove() via Version.fetch
        ("rest/account.ts", 64, "resource-write"),  # removeWithHttpInfo()
        ("rest/account.ts", 68, "resource-write"),  # patch()
        ("rest/message.ts", 14, "resource-write"),  # factory create()
        ("rest/message.ts", 18, "resource-write"),  # factory remove()
    }

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_fixture_layout_flags_writes_not_reads(self):
        with tempfile.TemporaryDirectory() as td:
            root = _copy_fixtures(pathlib.Path(td) / "repo")
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        rest = {f for f in _findings(out) if f[0].startswith("rest/")}
        self.assertEqual(rest, self.EXPECTED, out)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_json_mode_reports_resource_finding(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            (root / "rest").mkdir(parents=True)
            (root / "rest" / "account.ts").write_text(
                "class Version {\n"
                "  update(opts: any) { return this.request(opts); }\n"
                "}\n"
                "class AccountContext {\n"
                "  constructor(private version: Version) {}\n"
                "  update() {\n"
                "    return this.version.update({ uri: \"/x\", method: \"post\" });\n"
                "  }\n"
                "  fetch() {\n"
                "    return this.version.fetch({ uri: \"/x\", method: \"get\" });\n"
                "  }\n"
                "}\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.scan_cmd(_args(root, pathlib.Path(td) / "policy.json",
                                          format="json"))
            out = buf.getvalue()
        self.assertEqual(code, 0)
        doc = __import__("json").loads(out)
        self.assertEqual(doc["files_scanned"], 1)
        findings = doc["findings"]
        self.assertEqual(len(findings), 1, doc)
        f = findings[0]
        self.assertEqual((f["file"], f["line"], f["function"], f["verb"]),
                         ("rest/account.ts", 7, "update", "rest.update"))
        self.assertEqual((f["kind"], f["language"], f["gated"]),
                         ("http", "tsjs", False))
        self.assertIn('method: "post"', f["snippet"])


class MissingExtraTest(unittest.TestCase):
    BLOCK = [
        "  " + "-" * 64,
        "  WARNING: 2 TS/JS file(s) were seen but none were scanned.",
        "  The polyglot extra is not installed, so this report covers",
        "  Python only. Zero TS/JS findings is a coverage gap, not a",
        "  clean result.",
        "  Install it with: pip install 'pywrit[polyglot]'",
        "  " + "-" * 64,
    ]

    def _repo(self, root, with_python=True):
        (root / "web").mkdir()
        (root / "web" / "a.ts").write_text(FileWalkTest.WRITE)
        (root / "web" / "b.js").write_text(FileWalkTest.WRITE)
        if with_python:
            (root / "orders.py").write_text(
                'def create_order(db):\n    db.execute("INSERT INTO o VALUES (1)")\n')

    def _last_line(self, out):
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    def test_prominent_block_once_and_python_still_scanned(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._repo(root)
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                self.assertEqual(cli._tsjs_parsers(), {})
                code, out = _run_scan(root)
        self.assertEqual(code, 0)
        for line in self.BLOCK:
            self.assertIn(line, out)
        self.assertEqual(
            out.count("WARNING: 2 TS/JS file(s) were seen but none were "
                      "scanned."), 1)
        self.assertNotIn("hint:", out)
        self.assertIn("write sites: 1 in 1 function(s)", out)
        self.assertIn("orders.create", out)
        self.assertNotIn("ts/js files scanned", out)
        self.assertEqual(self._last_line(out), GitHubAppLineTest.LINE)

    def test_normal_path_qualified_verdict_on_ts_only_repo(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._repo(root, with_python=False)
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                code, out = _run_scan(root)
        self.assertEqual(code, 0)
        for line in self.BLOCK:
            self.assertIn(line, out)
        # the bare verdict must not stand while TS/JS went unscanned
        self.assertIn("No write operations discovered in the files that "
                      "were scanned.", out)
        self.assertNotIn("\nNo write operations discovered.\n", out)
        self.assertEqual(self._last_line(out), GitHubAppLineTest.LINE)

    def test_score_path_block_and_qualified_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._repo(root, with_python=False)
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                code, out = _run_scan(root, score=True)
        self.assertEqual(code, 0)
        for line in self.BLOCK:
            self.assertIn(line, out)
        self.assertIn("No write operations discovered in the files that "
                      "were scanned.", out)
        self.assertNotIn("\nNo write operations discovered.\n", out)
        self.assertEqual(self._last_line(out), GitHubAppLineTest.LINE)

    def test_json_report_records_unscanned_tsjs(self):
        import json as j
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._repo(root, with_python=False)
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                code, out = _run_scan(root, format="json")
            self.assertEqual(code, 0, out)
            doc = j.loads(out)
        self.assertTrue(doc["tsjs_hint"])
        self.assertEqual(doc["tsjs_not_scanned"], {
            "reason": "missing_extra",
            "extra": "pywrit[polyglot]",
            "files": 2,
            "install_command": "pip install 'pywrit[polyglot]'",
        })
        self.assertEqual(doc["findings"], [])
        self.assertIn("github_app", doc)

    def test_python_only_repo_output_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "orders.py").write_text(
                'def create_order(db):\n    db.execute("INSERT INTO o VALUES (1)")\n')
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertNotIn("hint:", out)
        self.assertNotIn("ts/js", out)
        self.assertTrue(out.startswith("writ scan: %s\n  files scanned: 1  skipped: 0\n"
                                       "  write sites: 1 in 1 function(s)\n"
                                       "  gated: 0/1 (0%%)\n  verbs discovered: 1\n"
                                       "    orders.create\n" % root.resolve()), out)


class NonProductScanTest(unittest.TestCase):
    """Axios-class noise: non-product paths are suppressed by default,
    counted per class with paths named, and restored by the flag."""

    WRITE = 'fetch("https://api.example.com/x", {method: "POST"})\n'

    def _layout(self, root):
        (root / "lib").mkdir(parents=True)
        (root / "lib" / "core.js").write_text(self.WRITE)
        for d in ("docs/scripts", "scripts", "sandbox", "examples"):
            p = root / d
            p.mkdir(parents=True)
            (p / "tool.js").write_text(self.WRITE)
        (root / "gulpfile.js").write_text(self.WRITE)
        (root / "lib" / "benchmark-utils.ts").write_text(self.WRITE)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_suppressed_by_default_and_restored_by_flag(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._layout(root)
            res = cli._tsjs_scan(root, [])
            self.assertEqual(len(res["sites"]), 2)  # lib/core.js + benchmark-utils.ts
            total = cli._tsjs_suppressed_total(res["suppressed"])
            self.assertEqual(total, 5)
            res2 = cli._tsjs_scan(root, [], include_non_product=True)
            self.assertEqual(len(res2["sites"]), 7)
            self.assertEqual(res2["suppressed"], {})

    def test_path_class_units(self):
        root = pathlib.Path("/repo")
        self.assertEqual(
            cli._tsjs_non_product_class(root / "docs" / "a.js", root), "docs")
        self.assertEqual(
            cli._tsjs_non_product_class(root / "gulpfile.js", root),
            "build-tooling")
        self.assertIsNone(
            cli._tsjs_non_product_class(root / "lib" / "benchmark-utils.ts",
                                        root))
        self.assertIsNone(
            cli._tsjs_non_product_class(root / "lib" / "core.js", root))


class GitHubAppLineTest(unittest.TestCase):
    """Regression: every scan report ends with the GitHub App line.

    The local scan is invisible by design; the GitHub App is the visible
    surface. The text report's last line points at it on every outcome
    (findings found, zero findings, suppressed-only, --score), and the
    JSON report carries the same pointer under `github_app`.
    """

    LINE = ("Run this scan on every push and pull request with the Writ "
            "GitHub App: check runs on each change, history in the portal. "
            "Install: https://github.com/apps/writ-scanner "
            "(guide: https://docs.withwrit.com/git-hub-app)")

    FINDING_REPO = {
        "app.py": ('import requests\n\n\n'
                   'def send(url):\n'
                   '    return requests.post(url, json={})\n'),
    }
    CLEAN_REPO = {
        "app.py": ('def read():\n'
                   '    return open("/tmp/x").read()\n'),
    }

    def _repo(self, root, files):
        for rel, src in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(src)

    def _last_line(self, out):
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    def test_findings_found_run_ends_with_app_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            self._repo(root, self.FINDING_REPO)
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertIn("write sites: 1 in 1 function(s)", out)
        self.assertEqual(self._last_line(out), self.LINE)

    def test_zero_findings_run_ends_with_app_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            self._repo(root, self.CLEAN_REPO)
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertIn("write sites: 0 in 0 function(s)", out)
        self.assertEqual(self._last_line(out), self.LINE)

    def test_score_only_run_ends_with_app_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            self._repo(root, self.FINDING_REPO)
            code, out = _run_scan(root, score=True)
        self.assertEqual(code, 0)
        self.assertEqual(self._last_line(out), self.LINE)

    def test_json_report_carries_github_app_field(self):
        import json as j
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            self._repo(root, self.FINDING_REPO)
            code, out = _run_scan(root, format="json")
            self.assertEqual(code, 0, out)
            app = j.loads(out)["github_app"]
        self.assertEqual(app, {
            "install_url": "https://github.com/apps/writ-scanner",
            "docs_url": "https://docs.withwrit.com/git-hub-app",
            "note": ("Run this scan on every push and pull request with "
                     "the Writ GitHub App: check runs on each change, "
                     "history in the portal."),
        })

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_suppressed_only_run_ends_with_app_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            root.mkdir()
            self._repo(root, {
                "docs/scripts/tool.js": NonProductScanTest.WRITE * 3,
            })
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertIn("ts/js write sites: 0 in 0 function(s)", out)
        self.assertIn("ts/js non-product: 3 site(s) suppressed", out)
        self.assertEqual(self._last_line(out), self.LINE)


class CliSyncTest(unittest.TestCase):
    def test_download_copy_is_byte_identical(self):
        web = HERE.parent.parent / "gate" / "web" / "writ"
        if not web.exists():
            self.skipTest("gate/web/writ not present")
        self.assertEqual(web.read_bytes(),
                         (HERE.parent / "src" / "pywrit" / "cli.py").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
