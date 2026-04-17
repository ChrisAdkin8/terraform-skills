# terraform-skills MCP server

Cross-harness [Model Context Protocol](https://modelcontextprotocol.io) server exposing the `tf-analyze`, `tf-test`, `tf-refactor`, and `tf-cost` workflows. Works with any MCP-capable harness — Claude Desktop, Cursor, Cline, Zed, Continue, Claude Code (via `claude mcp add`), or your own client.

The server is a thin wrapper around the same scripts the [Claude Code skills](../claude-skills/) use — `detect.py`, the catalogue, `terraform`, `infracost`. No forked logic.

---

## Install

From this directory:

```bash
pip install -e .
# or
uv pip install -e .
```

This exposes a console script `terraform-skills-mcp` that the harness can launch.

### From PyPI (once published)

```bash
pip install terraform-skills-mcp
```

When installing from PyPI (not from a repo checkout), set `TERRAFORM_SKILLS_ROOT` to a checkout of the repo so the server can find the shared `claude-skills/tf-analyze/catalog/` and `scripts/detect.py`:

```bash
export TERRAFORM_SKILLS_ROOT=$HOME/src/terraform-skills
```

---

## Wire it into a harness

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "terraform-skills": {
      "command": "terraform-skills-mcp",
      "env": {
        "INFRACOST_API_KEY": "…",
        "TERRAFORM_SKILLS_ROOT": "/absolute/path/to/terraform-skills"
      }
    }
  }
}
```

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "terraform-skills": {
      "command": "terraform-skills-mcp"
    }
  }
}
```

### Cline (VS Code)

In the Cline sidebar → MCP Servers → Add Server:

- Name: `terraform-skills`
- Command: `terraform-skills-mcp`

### Claude Code

```bash
claude mcp add terraform-skills terraform-skills-mcp
```

### Zed / Continue / custom

Any MCP client that speaks stdio transport. Point it at the `terraform-skills-mcp` command.

---

## Tool reference

### `tf_analyze(path, mode?, output_format?, diff_base?, prior_report?, fail_on?)`

Run the deterministic detection pass against a directory of `.tf` files. Returns findings in the requested format (defaults to JSON).

- `path` — directory to scan.
- `mode` — `static` (full scan), `diff` (changed files vs `diff_base`), or `verify-fixed`.
- `output_format` — `text`, `json` (recommended), `sarif`, or `html`.
- `diff_base` — git ref when `mode=diff` (e.g. `"main"`).
- `prior_report` — path to prior markdown/json report when `mode=verify-fixed`.
- `fail_on` — severity threshold (`CRITICAL` | `HIGH` | `MEDIUM` | `LOW` | `INFO`).

### `tf_analyze_list_catalog()`

Returns every catalogue entry as `{id, title, severity, focus, status, file}`. 60 rules covering security, robustness, ops, modules, cost-risk, and CI-test hygiene.

### `tf_analyze_get_catalog_entry(entry_id)`

Returns the full YAML definition of a single catalogue entry — detection pattern, CIS mapping, remediation guidance, linked fixtures.

### `tf_analyze_verify_fixed(path, prior_report)`

Re-probe every finding location in a prior report. Each prior finding is tagged `resolved`, `still-present`, or `moved`.

---

### `tf_cost_breakdown(path, tfvars_file?, usage_file?, output_format?)`

Monthly cost estimate for a Terraform directory. Wraps `infracost breakdown`. Requires `infracost` on PATH and `INFRACOST_API_KEY`.

### `tf_cost_diff(path, compare_to?, tfvars_file?, usage_file?)`

Cost delta between current state and a plan. Wraps `infracost diff`.

### `tf_cost_budget_check(path, monthly_budget_usd, tfvars_file?, usage_file?)`

Assert monthly cost is under a threshold. Returns `{ok, monthly_usd, budget_usd, delta_usd}`.

---

### `tf_refactor_plan(path)`

Run `terraform plan` and summarise: adds, changes, destroys, replaces, moved blocks. `ok=true` only when destroys=0 and replaces=0.

### `tf_refactor_generate_moved(from_address, to_address)`

Render a `moved` block for renames without destroy/recreate. Terraform ≥ 1.1.

### `tf_refactor_generate_import(resource_address, resource_id, provider?)`

Render an `import` block for adopting existing resources into state. Terraform ≥ 1.5.

### `tf_refactor_generate_removed(resource_address, destroy?)`

Render a `removed` block for forgetting a resource from state (optionally destroying the real object). Terraform ≥ 1.7. Defaults to `destroy=false`.

---

### `tf_test_run(path, filter_file?, verbose?)`

Run `terraform test`. Returns `{ok, exit_code, stdout, stderr}`.

### `tf_test_list(path)`

List every `.tftest.hcl` file under a directory.

### `tf_test_scaffold(path, kind?, tests_subdir?, overwrite?)`

Scaffold baseline test files (defaults, validation, outputs, naming; plus phase-gate for scenarios). Does not overwrite unless `overwrite=true`.

---

## Environment variables

| Variable | Required for | Purpose |
|---|---|---|
| `TERRAFORM_SKILLS_ROOT` | Packaged install (pip from PyPI) | Points to a checkout of this repo so the server finds `claude-skills/tf-analyze/catalog/` and `scripts/detect.py`. Not needed when running from a repo clone. |
| `INFRACOST_API_KEY` | Any `tf_cost_*` tool | Infracost auth. Free tier — `infracost auth login`. |
| `GOOGLE_CREDENTIALS` / `GOOGLE_APPLICATION_CREDENTIALS` | `tf_refactor_plan` against real GCP state | Read-only creds for `terraform plan`. |
| `HCP_CLIENT_ID`, `HCP_CLIENT_SECRET` | HCP resources in `tf_refactor_plan` | HCP auth. |

---

## Development

```bash
pip install -e '.[dev]'
pytest
```

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the style guide and the rule that new deterministic capabilities must be added to both surfaces.

---

## Why not put the playbook in the MCP server too?

MCP tool descriptions are short and advertised upfront — they're not the right place for the multi-step procedural guidance the SKILL.md bodies carry (pre-flights, failure-mode triage, composition with other skills). The consuming harness's system prompt or rules file is the right place for that.

If you want the full playbook in another harness, paste the relevant `SKILL.md` body (from [`../claude-skills/<skill>/SKILL.md`](../claude-skills/)) into that harness's system prompt or rules file. The markdown is portable — only the frontmatter and `$ARGUMENTS` are Claude-Code-specific.
