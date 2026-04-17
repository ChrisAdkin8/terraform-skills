"""Smoke tests — confirm the server imports and the catalog is locatable.

These tests deliberately avoid invoking `terraform`, `infracost`, or any cloud
API. The goal is: can the package be installed, can the tools be registered,
can the shared assets under `claude-skills/tf-analyze/` be found.
"""

from __future__ import annotations

import importlib

import pytest


def test_package_imports():
    mod = importlib.import_module("terraform_skills_mcp")
    assert mod.__version__


def test_server_module_imports():
    importlib.import_module("terraform_skills_mcp.server")


def test_paths_resolve_to_claude_skills():
    from terraform_skills_mcp._paths import repo_root, tf_analyze_catalog, tf_analyze_scripts

    root = repo_root()
    assert (root / "claude-skills").is_dir()
    assert (root / "mcp").is_dir()

    catalog = tf_analyze_catalog()
    assert catalog.is_dir()
    yamls = list(catalog.glob("*.yaml"))
    assert yamls, "expected at least one catalog entry"

    scripts = tf_analyze_scripts()
    assert (scripts / "detect.py").is_file()


def test_list_catalog_returns_entries():
    from terraform_skills_mcp.tools.analyze import register

    class Capture:
        def __init__(self):
            self.fns = {}

        def tool(self):
            def decorator(fn):
                self.fns[fn.__name__] = fn
                return fn

            return decorator

    cap = Capture()
    register(cap)
    entries = cap.fns["tf_analyze_list_catalog"]()
    assert isinstance(entries, list)
    assert len(entries) > 0
    assert all("id" in e for e in entries)


def test_refactor_generate_moved_block():
    from terraform_skills_mcp.tools.refactor import register

    class Capture:
        def __init__(self):
            self.fns = {}

        def tool(self):
            def decorator(fn):
                self.fns[fn.__name__] = fn
                return fn

            return decorator

    cap = Capture()
    register(cap)
    hcl = cap.fns["tf_refactor_generate_moved"]("old.addr", "new.addr")
    assert "moved {" in hcl
    assert "from = old.addr" in hcl
    assert "to   = new.addr" in hcl
