"""writ_scan tool tests, mocked scanner, no network."""

import json
import os
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

from writ_mcp import server

INSTALL_CMD = 'pip install "pywrit[polyglot]"'


class _FakeSite:
    __slots__ = ("file", "func", "cls", "lineno", "kind", "snippet")

    def __init__(self, file, func, cls, lineno, kind, snippet):
        self.file = file
        self.func = func
        self.cls = cls
        self.lineno = lineno
        self.kind = kind
        self.snippet = snippet


class _FakeVisitor:
    """Stand-in for _ScanVisitor: yields the sites the factory was handed."""

    def __init__(self, src, filename, sites):
        self.sites = sites
        self.gated = set()

    def visit(self, tree):
        return None


def _polyglot_res(files=(), sites=(), gated=(), suppressed=None,
                  missing_extra=False):
    return {"files": list(files), "skipped": [], "sites": list(sites),
            "gated": set(gated), "suppressed": suppressed or {},
            "missing_extra": missing_extra}


def _fake_writ_cli(root, py_sites=(), tsjs=None, go=None, record=None):
    """Build fake writ_cli / writ_cli.cli modules scanning `root`."""
    package = types.ModuleType("writ_cli")
    package.__path__ = []
    cli = types.ModuleType("writ_cli.cli")
    files = sorted(root / name for name, _site in py_sites)
    cli._collect_files = mock.Mock(return_value=files)
    cli._ast = mock.Mock()
    cli._ast.parse = mock.Mock(side_effect=lambda src: ("tree", src))
    by_file = {str(root / name): site for name, site in py_sites}

    def visitor(src, filename):
        sites = by_file.get(filename)
        return _FakeVisitor(src, filename, [sites] if sites else [])

    cli._ScanVisitor = visitor

    def infer_verb(rel, func, cls, kind):
        return "%s.inferred" % rel.stem

    cli.infer_verb = infer_verb
    cli._tsjs_verb = lambda rel, func, cls, kind: "%s.tsjs" % rel.stem
    cli._go_verb = lambda rel, func, cls, kind: "%s.go" % rel.stem

    def tsjs_scan(scan_root, excludes, include_non_product=False):
        if tsjs is None:
            raise AssertionError("_tsjs_scan must not be called")
        if record is not None:
            record["tsjs"] = {"root": scan_root, "excludes": excludes,
                              "include_non_product": include_non_product}
        return tsjs

    def go_scan(scan_root, excludes, include_non_product=False):
        if go is None:
            raise AssertionError("_go_scan must not be called")
        if record is not None:
            record["go"] = {"root": scan_root, "excludes": excludes,
                            "include_non_product": include_non_product}
        return go

    cli._tsjs_scan = mock.Mock(side_effect=tsjs_scan)
    cli._go_scan = mock.Mock(side_effect=go_scan)
    return {"writ_cli": package, "writ_cli.cli": cli}


@pytest.fixture
def root(tmp_path):
    root = Path(tmp_path).resolve()
    (root / "orders.py").write_text("x = 1\n", encoding="utf-8")
    (root / "app.ts").write_text("export {}\n", encoding="utf-8")
    (root / "main.go").write_text("package main\n", encoding="utf-8")
    return root


def _run_scan(monkeypatch, modules, **kwargs):
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    return json.loads(server.writ_scan(**kwargs))


def test_summary_shape_and_relative_findings(monkeypatch, root):
    py_site = _FakeSite(str(root / "orders.py"), "refund_order",
                        "", 3, "http", "requests.post(url)")
    ts_site = (_FakeSite(str(root / "app.ts"), "createUser",
                         "UserService", 7, "db",
                         "db.user.create({ data })"), "prisma-write",
               ("createUser", 5))
    go_site = (_FakeSite(str(root / "main.go"), "DeleteUser", "",
                         9, "db", "db.Exec(\"DELETE FROM users\")"),
               "go-sql-write", ("DeleteUser", 8))
    tsjs = _polyglot_res(
        files=[root / "app.ts"], sites=[ts_site],
        gated={(str(root / "app.ts"), "createUser", 5)},
        suppressed={"scripts": {"sites": 2,
                                "files": {str(root / "s" / "x.ts"): 2}}})
    go = _polyglot_res(files=[root / "main.go"], sites=[go_site])
    modules = _fake_writ_cli(
        root, py_sites=[("orders.py", py_site)], tsjs=tsjs, go=go)
    out = _run_scan(monkeypatch, modules, path=str(root))

    assert out["path"] == str(root)
    assert out["languages"]["python"] == {"files": 1, "skipped": 0, "sites": 1, "gated": 0}
    assert out["languages"]["tsjs"] == {"files": 1, "skipped": 0, "sites": 1, "gated": 1,
                                        "suppressed": {"scripts": 2}}
    assert out["languages"]["go"] == {"files": 1, "skipped": 0, "sites": 1, "gated": 0,
                                      "suppressed": {}}
    assert out["notScanned"] == {}
    assert out["verdict"] == "3 write operations discovered, 2 without a gate"
    assert out["findingsTruncated"] == 0

    findings = out["findings"]
    assert [f["file"] for f in findings] == ["app.ts", "main.go", "orders.py"]
    assert findings[0] == {"file": "app.ts", "line": 7, "kind": "db",
                           "function": "createUser", "class": "UserService",
                           "verb": "app.tsjs",
                           "snippet": "db.user.create({ data })"}
    assert findings[1]["verb"] == "main.go"
    assert findings[1]["function"] == "DeleteUser"
    assert findings[2]["verb"] == "orders.inferred"
    assert findings[2]["kind"] == "http"
    assert findings[2]["snippet"] == "requests.post(url)"
    assert not any(os.path.isabs(f["file"]) for f in findings)


def test_all_gated_verdict(monkeypatch, root):
    py_site = _FakeSite(str(root / "orders.py"), "refund", "",
                        2, "db", "cursor.execute(sql)")
    modules = _fake_writ_cli(root,
                             py_sites=[("orders.py", py_site)],
                             tsjs=_polyglot_res(), go=_polyglot_res())

    def visitor(src, filename, _site=py_site):
        v = _FakeVisitor(src, filename, [_site])
        v.gated = {("refund", 1)}
        return v

    modules["writ_cli.cli"]._ScanVisitor = visitor
    out = _run_scan(monkeypatch, modules, path=str(root))
    assert out["languages"]["python"]["gated"] == 1
    assert out["verdict"] == "1 write operations discovered; all 1 gated"


def test_python_only_verdict_and_no_write_verdict(monkeypatch, root):
    ts_site = (_FakeSite(str(root / "app.ts"), "createUser", "",
                         7, "db", "db.user.create({ data })"),
               "prisma-write", ("createUser", 5))
    tsjs = _polyglot_res(files=[root / "app.ts"], sites=[ts_site])
    modules = _fake_writ_cli(root, tsjs=tsjs, go=_polyglot_res())
    out = _run_scan(monkeypatch, modules, path=str(root))
    assert out["verdict"] == "No Python write operations discovered."

    modules = _fake_writ_cli(root, tsjs=_polyglot_res(),
                             go=_polyglot_res())
    out = _run_scan(monkeypatch, modules, path=str(root))
    assert out["verdict"] == "No write operations discovered."
    assert out["findings"] == []


def test_cap_and_findings_truncated(monkeypatch, root):
    py_sites = []
    for name in ("a.py", "b.py", "c.py"):
        (root / name).write_text("x = 1\n", encoding="utf-8")
        py_sites.append((name, _FakeSite(str(root / name), "write",
                                         "", 1, "file",
                                         "open(p, 'w')")))
    modules = _fake_writ_cli(root, py_sites=py_sites,
                             tsjs=_polyglot_res(), go=_polyglot_res())
    out = _run_scan(monkeypatch, modules, path=str(root), max_findings=2)
    assert len(out["findings"]) == 2
    assert out["findingsTruncated"] == 1
    assert [f["file"] for f in out["findings"]] == ["a.py", "b.py"]

    out = _run_scan(monkeypatch, modules, path=str(root))
    assert len(out["findings"]) == 3
    assert out["findingsTruncated"] == 0


def test_include_non_product_passthrough(monkeypatch, root):
    record = {}
    modules = _fake_writ_cli(root, tsjs=_polyglot_res(),
                             go=_polyglot_res(), record=record)
    _run_scan(monkeypatch, modules, path=str(root), include_non_product=True)
    assert record["tsjs"]["include_non_product"] is True
    assert record["go"]["include_non_product"] is True
    assert record["tsjs"]["excludes"] == []
    assert record["go"]["excludes"] == []
    assert record["tsjs"]["root"] == root

    record = {}
    modules = _fake_writ_cli(root, tsjs=_polyglot_res(),
                             go=_polyglot_res(), record=record)
    _run_scan(monkeypatch, modules, path=str(root))
    assert record["tsjs"]["include_non_product"] is False
    assert record["go"]["include_non_product"] is False


def test_missing_polyglot_extra(monkeypatch, root):
    tsjs = _polyglot_res(files=[root / "app.ts"], missing_extra=True)
    go = _polyglot_res(files=[root / "main.go"], missing_extra=True)
    modules = _fake_writ_cli(root, tsjs=tsjs, go=go)
    out = _run_scan(monkeypatch, modules, path=str(root))

    for lang, key in (("tsjs", "TS/JS"), ("go", "Go")):
        entry = out["notScanned"][lang]
        assert entry["language"] == lang
        assert entry["filesSeen"] == 1
        assert entry["filesScanned"] == 0
        assert entry["install"] == INSTALL_CMD
        assert key in entry["warning"]
        assert "were seen but none were scanned" in entry["warning"]
        assert "coverage gap, not a clean result" in entry["warning"]
    assert out["languages"]["tsjs"]["files"] == 1
    assert out["languages"]["tsjs"]["sites"] == 0
    assert out["languages"]["go"]["files"] == 1
    assert out["verdict"] == ("No write operations discovered in the files "
                              "that were scanned.")
    assert out["findings"] == []


def test_missing_path_returns_error_without_scanning(monkeypatch, root):
    modules = _fake_writ_cli(
        root,
        tsjs=_polyglot_res(files=[root / "app.ts"],
                           missing_extra=True),
        go=_polyglot_res())
    out = _run_scan(monkeypatch, modules,
                    path=str(root / "does-not-exist"))
    assert out["status"] == 400
    assert "does not exist" in out["error"]
    assert out["detail"]["path"] == str(root / "does-not-exist")
    modules["writ_cli.cli"]._collect_files.assert_not_called()
    modules["writ_cli.cli"]._tsjs_scan.assert_not_called()
    modules["writ_cli.cli"]._go_scan.assert_not_called()


def test_file_path_is_not_a_directory(monkeypatch, root):
    modules = _fake_writ_cli(root, tsjs=None, go=None)
    out = _run_scan(monkeypatch, modules, path=str(root / "orders.py"))
    assert out["status"] == 400
    assert "not a directory" in out["error"]
    modules["writ_cli.cli"]._collect_files.assert_not_called()
    modules["writ_cli.cli"]._tsjs_scan.assert_not_called()
    modules["writ_cli.cli"]._go_scan.assert_not_called()


def test_pywrit_missing_error_names_install_command(monkeypatch, root):
    out = _run_scan(monkeypatch, {"writ_cli": None, "writ_cli.cli": None},
                    path=str(root))
    assert out["status"] == 0
    assert "pywrit" in out["error"]
    assert out["detail"] == {"install": INSTALL_CMD}
    assert out["detail"]["install"] == 'pip install "pywrit[polyglot]"'


def test_scanner_exception_returns_error_shape(monkeypatch, root):
    modules = _fake_writ_cli(root, tsjs=_polyglot_res(),
                             go=_polyglot_res())
    modules["writ_cli.cli"]._tsjs_scan.side_effect = RuntimeError(
        "tree-sitter blew up")
    out = _run_scan(monkeypatch, modules, path=str(root))
    assert out["status"] == 0
    assert "scan failed" in out["error"]
    assert out["detail"] == {"exception": "tree-sitter blew up"}
    assert "Traceback" not in json.dumps(out)
