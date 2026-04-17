"""MCP wrappers for the tf-analyze workflow.

These shell out to `claude-skills/tf-analyze/scripts/detect.py` — the same
script the Claude skill uses. The catalog and fixtures are read directly from
`claude-skills/tf-analyze/catalog/`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

import yaml

from .._paths import tf_analyze_catalog, tf_analyze_scripts


def _run_detect(args: list[str]) -> str:
    script = tf_analyze_scripts() / "detect.py"
    if not script.is_file():
        raise FileNotFoundError(f"detect.py not found at {script}")
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"detect.py failed (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout


def register(mcp) -> None:
    @mcp.tool()
    def tf_analyze(
        path: str,
        mode: Literal["static", "diff", "verify-fixed"] = "static",
        output_format: Literal["text", "json", "sarif", "html"] = "json",
        diff_base: str | None = None,
        prior_report: str | None = None,
        fail_on: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] | None = None,
    ) -> str:
        """Run the tf-analyze deterministic detection pass against a Terraform directory.

        Returns findings in the requested format (JSON by default — easiest for the
        consuming model to parse). Uses the same detect.py the Claude skill uses,
        so results match between surfaces.

        Args:
            path: Absolute or relative directory containing .tf files to scan.
            mode: static (full scan), diff (changed files only vs diff_base),
                  or verify-fixed (re-probe findings from a prior report).
            output_format: text | json | sarif | html. json recommended for LLM consumption.
            diff_base: Git ref to diff against when mode=diff (e.g. "main").
            prior_report: Path to a prior markdown/json report when mode=verify-fixed.
            fail_on: If set, the tool returns a non-zero-style payload when any
                     finding at this severity or higher is present.
        """
        args = ["--target", path, "--mode", mode, "--format", output_format]
        if diff_base:
            args += ["--diff-base", diff_base]
        if prior_report:
            args += ["--prior-report", prior_report]
        if fail_on:
            args += ["--fail-on", fail_on]
        return _run_detect(args)

    @mcp.tool()
    def tf_analyze_list_catalog() -> list[dict]:
        """List every catalogue entry with its ID, title, severity, and focus area.

        Returns a compact summary — use `tf_analyze_get_catalog_entry` to fetch the
        full YAML definition of a specific rule.
        """
        catalog = tf_analyze_catalog()
        entries: list[dict] = []
        for yml in sorted(catalog.glob("*.yaml")):
            try:
                data = yaml.safe_load(yml.read_text()) or {}
            except yaml.YAMLError:
                continue
            entries.append(
                {
                    "id": data.get("id") or yml.stem,
                    "title": data.get("title"),
                    "severity": data.get("severity") or data.get("default_urgency"),
                    "focus": data.get("focus") or data.get("section"),
                    "blast_radius": data.get("blast_radius"),
                    "status": data.get("status", "stable"),
                    "file": yml.name,
                }
            )
        return entries

    @mcp.tool()
    def tf_analyze_get_catalog_entry(entry_id: str) -> dict:
        """Fetch the full YAML catalogue entry for a given finding ID (e.g. 'SEC-IAM-001').

        Returns the entry's title, severity, blast radius, CIS mapping, detection
        pattern, remediation guidance, and linked fixtures.
        """
        catalog = tf_analyze_catalog()
        target = f"{entry_id}.yaml"
        path = catalog / target
        if not path.is_file():
            matches = [p for p in catalog.glob("*.yaml") if p.stem.lower() == entry_id.lower()]
            if not matches:
                raise FileNotFoundError(f"No catalogue entry with id {entry_id!r}")
            path = matches[0]
        return yaml.safe_load(path.read_text())

    @mcp.tool()
    def tf_analyze_verify_fixed(path: str, prior_report: str) -> str:
        """Re-probe every finding location in a prior tf-analyze report.

        Use this between full runs to confirm fixes landed without re-scanning the
        entire repo. Returns JSON: each prior finding tagged as 'resolved',
        'still-present', or 'moved'.
        """
        return _run_detect(
            [
                "--target",
                path,
                "--mode",
                "verify-fixed",
                "--prior-report",
                prior_report,
                "--format",
                "json",
            ]
        )
