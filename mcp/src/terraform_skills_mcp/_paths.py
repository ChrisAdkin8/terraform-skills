"""Resolve paths to shared assets that live under `claude-skills/`.

Both surfaces (Claude skills + MCP) read from the same catalog/fixtures/scripts
to stay in lockstep. When installed as a Python package, the MCP code still
needs to locate those files; we search upward from this file's location for the
repo root (marked by the presence of both `claude-skills/` and `mcp/`).

If the package is installed separately from the repo (e.g. published to PyPI
without the skill assets), callers must pass `TERRAFORM_SKILLS_ROOT` via env.
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("TERRAFORM_SKILLS_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "claude-skills").is_dir():
            return p
        raise FileNotFoundError(
            f"TERRAFORM_SKILLS_ROOT={env} does not contain claude-skills/"
        )

    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "claude-skills").is_dir() and (candidate / "mcp").is_dir():
            return candidate

    raise FileNotFoundError(
        "Could not locate terraform-skills repo root. "
        "Set TERRAFORM_SKILLS_ROOT to the repo root."
    )


def tf_analyze_scripts() -> Path:
    return repo_root() / "claude-skills" / "tf-analyze" / "scripts"


def tf_analyze_catalog() -> Path:
    return repo_root() / "claude-skills" / "tf-analyze" / "catalog"
