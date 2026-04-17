"""MCP wrappers for the tf-test workflow."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal


def _require_terraform() -> None:
    if not shutil.which("terraform"):
        raise RuntimeError("terraform binary not found on PATH.")


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
    return proc.returncode, proc.stdout, proc.stderr


_BASELINE_FILES: dict[str, str] = {
    "defaults.tftest.hcl": '''# Defaults test — verify the module plans cleanly with no inputs beyond required.

run "defaults" {
  command = plan

  # assert output shapes, not values — the scaffolder does not know your outputs
  # assert {
  #   condition     = output.id != null
  #   error_message = "module must emit an id output"
  # }
}
''',
    "validation.tftest.hcl": '''# Validation test — each variable's `validation` block fires on bad input.

variables {
  # put a known-bad value here that violates a validation rule
  # example = "not-a-valid-project-id"
}

run "validation_rejects_bad_input" {
  command         = plan
  expect_failures = [var.example]
}
''',
    "outputs.tftest.hcl": '''# Outputs test — outputs resolve and have the expected type.

run "outputs_are_typed" {
  command = plan

  # assert {
  #   condition     = can(tostring(output.name))
  #   error_message = "output.name must be a string"
  # }
}
''',
    "naming.tftest.hcl": '''# Naming test — resources follow the project naming convention.

run "names_match_convention" {
  command = plan

  # assert {
  #   condition     = can(regex("^prj-[a-z0-9-]+$", output.name))
  #   error_message = "name must match ^prj-[a-z0-9-]+$"
  # }
}
''',
}


def register(mcp) -> None:
    @mcp.tool()
    def tf_test_run(
        path: str,
        filter_file: str | None = None,
        verbose: bool = False,
    ) -> dict:
        """Run `terraform test` in a directory.

        Returns {'ok': bool, 'exit_code': int, 'stdout': str, 'stderr': str}.
        The default is plan-mode tests (no cloud creds required) unless the
        .tftest.hcl files explicitly set `command = apply`.
        """
        _require_terraform()
        args = ["terraform", "test"]
        if verbose:
            args.append("-verbose")
        if filter_file:
            args += ["-filter", filter_file]
        rc, out, err = _run(args, cwd=path)
        return {
            "ok": rc == 0,
            "exit_code": rc,
            "stdout": out,
            "stderr": err.strip(),
        }

    @mcp.tool()
    def tf_test_list(path: str) -> list[str]:
        """List every .tftest.hcl file under a directory, relative to that directory."""
        root = Path(path)
        if not root.is_dir():
            raise FileNotFoundError(f"{path} is not a directory")
        return sorted(str(p.relative_to(root)) for p in root.rglob("*.tftest.hcl"))

    @mcp.tool()
    def tf_test_scaffold(
        path: str,
        kind: Literal["module", "scenario"] = "module",
        tests_subdir: str = "tests",
        overwrite: bool = False,
    ) -> dict:
        """Scaffold baseline Terraform test files.

        Creates `<path>/<tests_subdir>/` with four baseline files — defaults,
        validation, outputs, naming. The files are commented placeholders; the
        consuming model should edit them to match the actual module's variables
        and outputs before running.

        Returns {'created': [paths], 'skipped': [paths]}. Does not overwrite
        existing files unless `overwrite=true`.
        """
        target_dir = Path(path) / tests_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        created: list[str] = []
        skipped: list[str] = []
        for name, body in _BASELINE_FILES.items():
            dest = target_dir / name
            if dest.exists() and not overwrite:
                skipped.append(str(dest))
                continue
            dest.write_text(body)
            created.append(str(dest))
        if kind == "scenario":
            phase_gate = target_dir / "phase_gate.tftest.hcl"
            if phase_gate.exists() and not overwrite:
                skipped.append(str(phase_gate))
            else:
                phase_gate.write_text(
                    '''# Phase-gate test — scenario applies in the expected order without regression.

run "phase_gate" {
  command = plan

  # assert that phase-2 resources don't appear before phase-1 completes.
  # Customise for your scenario's phase discriminator.
}
'''
                )
                created.append(str(phase_gate))
        return {"created": created, "skipped": skipped}
