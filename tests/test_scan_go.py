#!/usr/bin/env python3
"""Deterministic tests for `writ scan` Go support (slice 1).

Fixtures live in tests/fixtures/go. Every line tagged `// expect: <rule>`
must be reported with that rule, and nothing else may be reported.
Tests that parse Go skip when the optional `polyglot` extra (tree-sitter
plus tree-sitter-go) is not installed; the rest run with zero extra deps.
Mirrors test_scan_tsjs.py.
"""

import argparse
import contextlib
import io
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

FIXTURES = HERE / "fixtures" / "go"
HAVE_EXTRA = bool(cli._go_parsers())
_BLOCK_EXTRA = {m: None for m in ("tree_sitter", "tree_sitter_go",
                                  "tree_sitter_language_pack")}
_GO_RULES = {"go-db-write", "go-orm-write", "go-http-client-write",
             "go-http-request-write", "go-sdk-write"}
_EXPECT = re.compile(r"//\s*expect:\s*([a-z0-9-]+)")
_FINDING = re.compile(
    r"^    (?P<file>\S+\.go):(?P<line>\d+) \[(?P<kind>[a-z]+)\] "
    r"(?P<rule>go-[a-z0-9-]+) (?P<func>\S+)\(\): (?P<snippet>.+)$")


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
    for p in sorted(FIXTURES.rglob("*.go")):
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
        self.assertEqual(covered, _GO_RULES)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_negative_reads_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            shutil.copy(str(FIXTURES / "reads.go"), str(root / "reads.go"))
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertIn("go files scanned: 1  skipped: 0", out)
        self.assertIn("go write sites: 0 in 0 function(s)", out)
        self.assertEqual(_findings(out), set())
        self.assertIn("nothing to instrument.", out)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_output_format_counts_and_verbs(self):
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
        self.assertIn("go files scanned: 5  skipped: 0  (scan only, no --apply)", out)
        self.assertIn("go write sites: %d in 6 function(s)" % n, out)
        self.assertIn("go gated: 0/%d (0%%)" % n, out)
        self.assertIn("    db.go:13 [db] go-db-write deleteOrder(): "
                      "db.Exec(\"DELETE FROM orders WHERE id = $1\", id)", out)
        self.assertIn("    sdk.go:6 [sdk] go-sdk-write chargeCard(): "
                      "sc.Charges.New(params)", out)
        for v in ("db.delete", "db.create", "http.submit", "sdk.charge",
                  "sdk.nested"):
            self.assertEqual(verbs.get(v), "require_grant", v)
        self.assertIn("nothing to instrument (go findings are scan-only", out)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_verdict_qualified_when_go_sites_exist(self):
        # The score verdict grades Python writes only. With Go sites
        # found and no Python write, the bare "No write operations
        # discovered." must not stand: it reads as if the repo had no
        # writes at all. Same rule as the TS/JS case.
        with tempfile.TemporaryDirectory() as td:
            root = _copy_fixtures(pathlib.Path(td) / "repo")
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        self.assertIn("No Python write operations discovered.", out)
        self.assertNotIn("\nNo write operations discovered.\n", out)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(lines[-1], GitHubAppLineTest.LINE)

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_apply_never_rewrites_go_but_still_gates_python(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "repo"
            (root / "orders").mkdir(parents=True)
            go = root / "orders" / "api.go"
            go.write_text('package orders\n\nfunc createOrder(db *sql.DB) {\n'
                          '\tdb.Exec("INSERT INTO o VALUES (1)")\n}\n')
            py = root / "orders" / "store.py"
            py.write_text('def create_order():\n'
                          '    with open("/tmp/o", "w") as f:\n'
                          '        f.write("o")\n')
            before = go.read_bytes()
            code, out = _run_scan(root, apply=True, yes=True)
            self.assertEqual(code, 0)
            self.assertEqual(go.read_bytes(), before)
            self.assertIn("_writ_check(\"orders.create\")", py.read_text())
            self.assertIn("orders/api.go:4 [db] go-db-write createOrder()", out)
            self.assertIn("applied 1 gate(s) to 1 file(s).", out)


class FileWalkTest(unittest.TestCase):
    """Go file collection is stdlib-only; runs with or without the extra."""

    WRITE = 'package main\n\nfunc f() { db.Exec("DELETE FROM t") }\n'

    def _tree(self, root, rels):
        for rel in rels:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.WRITE)

    def test_skip_dirs_and_test_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            skipped = ["cmd/app/main_test.go", "vendor/lib/v.go",
                       "tests/a.go", "testing/a.go", ".git/hooks/x.go",
                       "node_modules/x/y.go", "src/readme.md", "src/a.ts"]
            kept = ["cmd/app/main.go", "internal/db/store.go", "a.go"]
            self._tree(root, skipped + kept)
            got = [str(p.relative_to(root))
                   for p in cli._go_collect_files(root, [])]
        self.assertEqual(sorted(got), sorted(kept))

    def test_exclude_substring(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._tree(root, ["src/a.go", "generated/b.go"])
            got = [str(p.relative_to(root))
                   for p in cli._go_collect_files(root, ["generated"])]
        self.assertEqual(got, ["src/a.go"])

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_respects_gitignore_inside_git_repo(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("generated/\n*.gen.go\n")
            self._tree(root, ["src/a.go", "generated/b.go", "src/c.gen.go",
                              "vendor/x/y.go"])
            got = [str(p.relative_to(root))
                   for p in cli._go_collect_files(root, [])]
        self.assertEqual(got, ["src/a.go"])


class MissingExtraTest(unittest.TestCase):
    BLOCK = [
        "  " + "-" * 64,
        "  WARNING: 2 Go file(s) were seen but none were scanned.",
        "  The polyglot extra is not installed, so this report covers",
        "  Python only. Zero Go findings is a coverage gap, not a",
        "  clean result.",
        "  Install it with: pip install 'pywrit[polyglot]'",
        "  " + "-" * 64,
    ]
    BOTH = [
        "  WARNING: 1 TS/JS file(s) and 1 Go file(s) were seen but none "
        "were scanned.",
        "  Python only. Zero TS/JS or Go findings is a coverage gap, not a",
    ]

    def _repo(self, root, with_python=True):
        (root / "cmd").mkdir()
        (root / "cmd" / "a.go").write_text(FileWalkTest.WRITE)
        (root / "cmd" / "b.go").write_text(FileWalkTest.WRITE)
        if with_python:
            (root / "orders.py").write_text(
                'def create_order(db):\n    db.execute("INSERT INTO o VALUES (1)")\n')

    def _last_line(self, out):
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return lines[-1] if lines else ""

    def test_go_only_repo_block_counts_go_files_and_verdict_qualified(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._repo(root, with_python=False)
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                self.assertEqual(cli._go_parsers(), {})
                code, out = _run_scan(root)
        self.assertEqual(code, 0)
        for line in self.BLOCK:
            self.assertIn(line, out)
        self.assertEqual(
            out.count("WARNING: 2 Go file(s) were seen but none were "
                      "scanned."), 1)
        # the bare verdict must not stand while Go files went unscanned
        self.assertIn("No write operations discovered in the files that "
                      "were scanned.", out)
        self.assertNotIn("\nNo write operations discovered.\n", out)
        self.assertNotIn("go files scanned", out)
        self.assertNotIn("ts/js files scanned", out)
        self.assertEqual(self._last_line(out), GitHubAppLineTest.LINE)

    def test_block_counts_both_languages(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "a.go").write_text(FileWalkTest.WRITE)
            (root / "b.ts").write_text(
                'export function f(){ return fetch("/x", { method: "POST" }); }\n')
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                code, out = _run_scan(root)
        self.assertEqual(code, 0)
        for line in self.BOTH:
            self.assertIn(line, out)
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
        self.assertEqual(self._last_line(out), GitHubAppLineTest.LINE)

    def test_json_report_records_unscanned_go(self):
        import json as j
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._repo(root, with_python=False)
            with mock.patch.dict(sys.modules, _BLOCK_EXTRA):
                code, out = _run_scan(root, format="json")
            self.assertEqual(code, 0, out)
            doc = j.loads(out)
        self.assertTrue(doc["go_hint"])
        self.assertEqual(doc["go_not_scanned"], {
            "reason": "missing_extra",
            "extra": "pywrit[polyglot]",
            "files": 2,
            "install_command": "pip install 'pywrit[polyglot]'",
        })
        self.assertEqual(doc["findings"], [])
        self.assertIn("github_app", doc)


class JsonReportTest(unittest.TestCase):
    """`writ scan --format json` carries Go findings like TS/JS ones."""

    @unittest.skipUnless(HAVE_EXTRA, "polyglot extra not installed")
    def test_json_mode_reports_go_finding(self):
        import json as j
        with tempfile.TemporaryDirectory() as td:
            root = _copy_fixtures(pathlib.Path(td) / "repo")
            code, out = _run_scan(root, format="json")
        self.assertEqual(code, 0, out)
        doc = j.loads(out)
        self.assertFalse(doc["go_hint"])
        self.assertEqual(doc["files_scanned"], 5)
        go_findings = [f for f in doc["findings"]
                       if f["language"] == "go"]
        self.assertEqual(len(go_findings), len(_expected()), doc)
        f = next(f for f in go_findings if f["file"] == "db.go"
                 and f["line"] == 13)
        self.assertEqual((f["function"], f["verb"], f["kind"], f["gated"]),
                         ("deleteOrder", "db.delete", "db", False))
        self.assertIn('db.Exec("DELETE FROM orders', f["snippet"])


class GitHubAppLineTest(unittest.TestCase):
    """The GitHub App line is the last line of the report with Go sites."""

    LINE = ("Run this scan on every push and pull request with the Writ "
            "GitHub App: check runs on each change, history in the portal. "
            "Install: https://github.com/apps/writ-scanner "
            "(guide: https://docs.withwrit.com/git-hub-app)")

    def test_line_is_last_with_go_sites(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "a.go").write_text(FileWalkTest.WRITE)
            code, out = _run_scan(root)
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        self.assertEqual(lines[-1], self.LINE)


if __name__ == "__main__":
    unittest.main()
