"""MCP wrappers for the tf-cost workflow — shells out to Infracost."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Literal


def _require_infracost() -> None:
    if not shutil.which("infracost"):
        raise RuntimeError(
            "infracost binary not found on PATH. Install from https://www.infracost.io/docs/"
        )


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def register(mcp) -> None:
    @mcp.tool()
    def tf_cost_breakdown(
        path: str,
        tfvars_file: str | None = None,
        usage_file: str | None = None,
        output_format: Literal["json", "table", "html"] = "json",
    ) -> str:
        """Estimate monthly cost for a Terraform directory.

        Runs `infracost breakdown` against `path`. Returns JSON by default so the
        consuming model can parse line-items. Requires `infracost` on PATH and
        `INFRACOST_API_KEY` in env (run `infracost auth login` once).
        """
        _require_infracost()
        args = ["infracost", "breakdown", "--path", path, "--format", output_format]
        if tfvars_file:
            args += ["--terraform-var-file", tfvars_file]
        if usage_file:
            args += ["--usage-file", usage_file]
        return _run(args)

    @mcp.tool()
    def tf_cost_diff(
        path: str,
        compare_to: str | None = None,
        tfvars_file: str | None = None,
        usage_file: str | None = None,
    ) -> str:
        """Show the cost delta between the current state and a plan.

        Runs `infracost diff`. If `compare_to` is not provided, Infracost uses the
        current state as the baseline and the path's plan as the proposed state.
        Returns JSON.
        """
        _require_infracost()
        args = ["infracost", "diff", "--path", path, "--format", "json"]
        if compare_to:
            args += ["--compare-to", compare_to]
        if tfvars_file:
            args += ["--terraform-var-file", tfvars_file]
        if usage_file:
            args += ["--usage-file", usage_file]
        return _run(args)

    @mcp.tool()
    def tf_cost_budget_check(
        path: str,
        monthly_budget_usd: float,
        tfvars_file: str | None = None,
        usage_file: str | None = None,
    ) -> dict:
        """Assert that the monthly cost of a Terraform directory is under a budget.

        Returns {'ok': bool, 'monthly_usd': float, 'budget_usd': float, 'delta_usd': float}.
        The consuming model should treat `ok=false` as a gate that must either
        trigger human review or block apply.
        """
        _require_infracost()
        args = ["infracost", "breakdown", "--path", path, "--format", "json"]
        if tfvars_file:
            args += ["--terraform-var-file", tfvars_file]
        if usage_file:
            args += ["--usage-file", usage_file]
        raw = _run(args)
        data = json.loads(raw)
        monthly = float(data.get("totalMonthlyCost") or 0.0)
        return {
            "ok": monthly <= monthly_budget_usd,
            "monthly_usd": monthly,
            "budget_usd": monthly_budget_usd,
            "delta_usd": monthly - monthly_budget_usd,
        }
