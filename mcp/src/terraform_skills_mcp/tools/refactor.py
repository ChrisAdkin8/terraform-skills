"""MCP wrappers for the tf-refactor workflow.

The two interesting shapes here:

1. `tf_refactor_plan` — runs `terraform plan` and triages destroys in the output.
   Emits a structured summary the consuming model can reason about.
2. `tf_refactor_generate_*` — emit `moved` / `import` / `removed` HCL blocks
   with the right syntax for the current Terraform version. Pure string rendering
   — no `terraform` invocation. Deliberately cheap so the LLM can iterate on the
   block without repeated plans.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Literal


def _require_terraform() -> None:
    if not shutil.which("terraform"):
        raise RuntimeError("terraform binary not found on PATH.")


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)
    return proc.returncode, proc.stdout, proc.stderr


_DESTROY_RE = re.compile(r"^\s*#\s+(\S+)\s+will be destroyed", re.MULTILINE)
_REPLACE_RE = re.compile(r"^\s*#\s+(\S+)\s+must be replaced", re.MULTILINE)
_MOVED_RE = re.compile(r"^\s*#\s+(\S+)\s+has moved to\s+(\S+)", re.MULTILINE)


def register(mcp) -> None:
    @mcp.tool()
    def tf_refactor_plan(path: str) -> dict:
        """Run `terraform plan` and summarise change counts with destroys enumerated.

        Returns:
            {'ok': bool, 'adds': int, 'changes': int, 'destroys': int, 'replaces': int,
             'moved': [(from, to), ...], 'destroy_addresses': [...], 'stderr': str}

        `ok` is True only when destroys == 0 and replaces == 0 — the default
        safety posture for the refactor workflow. Any destroy/replace needs
        human triage before apply.
        """
        _require_terraform()
        rc, out, err = _run(["terraform", "plan", "-no-color"], cwd=path)
        destroys = _DESTROY_RE.findall(out)
        replaces = _REPLACE_RE.findall(out)
        moved = _MOVED_RE.findall(out)
        add_match = re.search(r"Plan:\s+(\d+)\s+to add,\s+(\d+)\s+to change,\s+(\d+)\s+to destroy", out)
        if add_match:
            adds, changes, declared_destroys = (int(x) for x in add_match.groups())
        else:
            adds = changes = declared_destroys = 0
        return {
            "ok": rc == 0 and declared_destroys == 0 and not replaces,
            "exit_code": rc,
            "adds": adds,
            "changes": changes,
            "destroys": declared_destroys,
            "replaces": len(replaces),
            "moved": [{"from": f, "to": t} for f, t in moved],
            "destroy_addresses": destroys,
            "replace_addresses": replaces,
            "stderr": err.strip(),
        }

    @mcp.tool()
    def tf_refactor_generate_moved(from_address: str, to_address: str) -> str:
        """Render a `moved` block for renaming a resource without destroy/recreate.

        Requires Terraform >= 1.1. Emit the returned HCL into a .tf file in the
        module, then run `terraform plan` — the plan should show 0 adds, 0 changes,
        0 destroys if the `to_address` is structurally identical to `from_address`.
        """
        return (
            f"moved {{\n"
            f"  from = {from_address}\n"
            f"  to   = {to_address}\n"
            f"}}\n"
        )

    @mcp.tool()
    def tf_refactor_generate_import(
        resource_address: str,
        resource_id: str,
        provider: str | None = None,
    ) -> str:
        """Render an `import` block for adopting an existing resource into state.

        Requires Terraform >= 1.5. The resource block itself still needs to be
        written separately — this block only says "the resource at address X
        corresponds to provider-object id Y". After applying, delete the import
        block.
        """
        body = [
            f"  to = {resource_address}",
            f'  id = "{resource_id}"',
        ]
        if provider:
            body.insert(0, f"  provider = {provider}")
        return "import {\n" + "\n".join(body) + "\n}\n"

    @mcp.tool()
    def tf_refactor_generate_removed(
        resource_address: str,
        destroy: Literal["true", "false"] = "false",
    ) -> str:
        """Render a `removed` block for forgetting a resource from state.

        Requires Terraform >= 1.7. Setting `destroy=true` will destroy the real
        cloud object on apply; `destroy=false` (the default for this tool) only
        forgets it from state, leaving the real object alone. Prefer false unless
        you explicitly want destruction.
        """
        return (
            "removed {\n"
            f"  from = {resource_address}\n"
            "  lifecycle {\n"
            f"    destroy = {destroy}\n"
            "  }\n"
            "}\n"
        )
