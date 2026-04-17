<p align="center">
  <img src="banner.svg" alt="terraform-skills — analyze, test, refactor, cost workflows framed by HCL braces" width="100%"/>
</p>

# terraform-skills

Opinionated, composable, safety-first Terraform workflows for the GCP + HashiCorp stack — available in **two shapes**:

| Shape | Lives in | Works with |
|---|---|---|
| **Claude Code skills** | [`claude-skills/`](claude-skills/) | Claude Code only (native slash-command + auto-invoke) |
| **MCP server** | [`mcp/`](mcp/) | Any MCP-capable harness — Claude Desktop, Cursor, Cline, Zed, Continue, etc. |

Both shapes wrap the same underlying logic — same catalogue, same fixtures, same `terraform`/`infracost` commands. Pick the shape that matches your harness.

## The four workflows

| Workflow | Purpose | Claude skill | MCP tools |
|---|---|---|---|
| `tf-analyze` | Static + plan-time analysis with 60 catalogue-backed findings, CIS mapping, delta tracking. | [`claude-skills/tf-analyze/`](claude-skills/tf-analyze/) | `tf_analyze`, `tf_analyze_list_catalog`, `tf_analyze_get_catalog_entry`, `tf_analyze_verify_fixed` |
| `tf-test` | Scaffold + run `terraform test` (HCL-native) with `mock_provider`. | [`claude-skills/tf-test/`](claude-skills/tf-test/) | `tf_test_run`, `tf_test_list`, `tf_test_scaffold` |
| `tf-refactor` | Safe rename / extract / import / remove using `moved` / `import` / `removed` blocks. | [`claude-skills/tf-refactor/`](claude-skills/tf-refactor/) | `tf_refactor_plan`, `tf_refactor_generate_moved`, `tf_refactor_generate_import`, `tf_refactor_generate_removed` |
| `tf-cost` | Monthly cost estimate, plan-time dollar diffs, budget gating. Wraps Infracost. | [`claude-skills/tf-cost/`](claude-skills/tf-cost/) | `tf_cost_breakdown`, `tf_cost_diff`, `tf_cost_budget_check` |

See [docs/harness-compatibility.md](docs/harness-compatibility.md) for how the two surfaces compare, and [docs/composition.md](docs/composition.md) for how the four workflows chain.

---

## Table of contents

- [Which shape should I use?](#which-shape-should-i-use)
- [Claude Code skills](#claude-code-skills)
- [MCP server](#mcp-server)
- [Prerequisites](#prerequisites)
- [Cloud scope](#cloud-scope)
- [Compatibility matrix](#compatibility-matrix)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Which shape should I use?

- **Using Claude Code?** → install the skills (see [below](#claude-code-skills)). You get slash-command invocation (`/tf-analyze`), auto-discovery, progressive disclosure, and playbook-driven judgement baked into each `SKILL.md`.
- **Using any other harness (Cursor, Cline, Zed, Claude Desktop, raw API)?** → run the MCP server (see [below](#mcp-server)). You get the deterministic tools; the harness's own prompting does the judgement.
- **Using both?** → install both. They share the same `claude-skills/tf-analyze/catalog/`, `fixtures/`, and `scripts/detect.py`, so versions stay in lockstep.

The Claude skills are the richer surface — they encode procedure, pre-flight checks, and failure modes in the SKILL.md body, which Claude Code loads progressively. The MCP server is thinner on purpose: it exposes the *actions* (run detection, run test, generate HCL block, estimate cost) and lets the consuming model drive the procedure. The table in [docs/harness-compatibility.md](docs/harness-compatibility.md) spells out the delta.

---

## Claude Code skills

[Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills) are markdown files with YAML frontmatter that give Claude a pre-baked procedure. When invoked via `/<skill-name>` or automatically when relevant, the skill's body is prepended to the model's context.

Each skill lives in its own directory under `claude-skills/`:

```
claude-skills/tf-analyze/SKILL.md
claude-skills/tf-test/SKILL.md
claude-skills/tf-refactor/SKILL.md
claude-skills/tf-cost/SKILL.md
```

### Installation

Claude Code discovers skills in two locations:

1. **User-global**: `~/.claude/skills/<skill-name>/SKILL.md` — available in every project.
2. **Project-local**: `<repo>/.claude/skills/<skill-name>/SKILL.md` — committed to share with the team.

#### Option 1 — install script (recommended)

```bash
# User-global, symlinked (changes here propagate immediately — good for authoring)
./install.sh --target user --mode symlink

# User-global, copied (frozen snapshot — good for end users)
./install.sh --target user --mode copy

# Project-local, copied into the repo you run it from
./install.sh --target project --mode copy --project-dir /path/to/your/tf/repo

# Install only specific skills
./install.sh --target user --mode symlink --only tf-test,tf-cost
```

Run `./install.sh --help` for the full flag list.

#### Option 2 — manual

```bash
# User-global
mkdir -p ~/.claude/skills
cp -R claude-skills/tf-analyze claude-skills/tf-test claude-skills/tf-refactor claude-skills/tf-cost ~/.claude/skills/

# Project-local
mkdir -p /path/to/tf-repo/.claude/skills
cp -R claude-skills/tf-analyze /path/to/tf-repo/.claude/skills/
```

#### Option 3 — git submodule (for teams)

```bash
cd /path/to/tf-repo
git submodule add https://github.com/ChrisAdkin8/terraform-skills .claude/skills-vendor
ln -s ../skills-vendor/claude-skills/tf-analyze .claude/skills/tf-analyze
# … repeat per skill
```

### Verifying installation

In any Claude Code session, type `/` — the four skills should appear in the completion list. If not:

```bash
ls -la ~/.claude/skills/   # or <repo>/.claude/skills/
```

Confirm each `SKILL.md` is readable and has valid YAML frontmatter.

### Quick start

```
/tf-analyze mode:diff diff-base:main
/tf-test action:scaffold target:tf/modules/vault-pki
/tf-refactor action:rename target:tf/scenarios/prod from:google_compute_instance.old to:google_compute_instance.new
/tf-cost action:diff target:tf/scenarios/prod env:prod
```

See each skill's `SKILL.md` for the full argument reference — they all share a common `key:value` grammar documented in [docs/argument-grammar.md](docs/argument-grammar.md).

---

## MCP server

The MCP server exposes the same four workflows as [Model Context Protocol](https://modelcontextprotocol.io) tools. Any MCP-capable harness can consume them.

### Installation

```bash
cd mcp
pip install -e .
```

Or via `uv`:

```bash
cd mcp
uv pip install -e .
```

### Running the server

```bash
terraform-skills-mcp        # runs on stdio — the default MCP transport
```

### Wiring it into a harness

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "terraform-skills": {
      "command": "terraform-skills-mcp"
    }
  }
}
```

**Cursor** — add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "terraform-skills": {
      "command": "terraform-skills-mcp"
    }
  }
}
```

**Cline (VS Code)** — in Cline settings, add an MCP server with command `terraform-skills-mcp`.

**Claude Code** — `claude mcp add terraform-skills terraform-skills-mcp`.

See [`mcp/README.md`](mcp/README.md) for the full tool reference, environment variables, and integration notes for each harness.

---

## Prerequisites

| Tool | Version | Required for |
|---|---|---|
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | Latest | Claude skills shape |
| Python | ≥ 3.10 | MCP server, `tf-analyze` detection script |
| Terraform | ≥ 1.6 | `tf-test`, `tf-refactor` |
| Terraform | ≥ 1.7 | `tf-test` (`mock_provider`), `tf-refactor` (`removed` block) |
| [Infracost](https://www.infracost.io/docs/) | ≥ 0.10 | `tf-cost` |
| `INFRACOST_API_KEY` env var | n/a | `tf-cost` (free tier — `infracost auth login`) |
| `GOOGLE_CREDENTIALS` env var | n/a | All apply-mode operations |
| HCP creds (`HCP_CLIENT_ID`, `HCP_CLIENT_SECRET`) | n/a | Any target that touches HCP |
| Go toolchain | ≥ 1.21 | Optional — only if using `tf-test`'s Terratest fallback |

---

## Cloud scope

| Cloud / platform | Support |
|---|---|
| GCP | First-class — every example targets GCP |
| HashiCorp (Vault, Consul, Nomad, HCP) | First-class — provider-specific traps called out in each workflow |
| AWS | Works but not prioritised — examples need translation |
| Azure | Works but not prioritised — same |

The workflows encode HashiCorp-specific operational knowledge (Vault PKI patterns, Consul Dataplane, phase-gated applies, HCP tier pricing). For non-GCP, non-HashiCorp stacks, the workflows remain useful but examples will need adaptation.

---

## Compatibility matrix

| Workflow | Terraform min | Other deps |
|---|---|---|
| `tf-analyze` | 1.1 (static/diff); 1.5 (`mode:plan`) | Python ≥ 3.10, git |
| `tf-test` | 1.6 (1.7 for `mock_provider`) | Go ≥ 1.21 optional (Terratest fallback) |
| `tf-refactor` | 1.1 (`moved`), 1.5 (`import`), 1.7 (`removed`) | None |
| `tf-cost` | Any | Infracost ≥ 0.10, `INFRACOST_API_KEY` |

| Harness | Claude skills | MCP server |
|---|---|---|
| Claude Code | ✓ native | ✓ via `claude mcp add` |
| Claude Desktop | ✗ | ✓ |
| Cursor | ✗ | ✓ |
| Cline | ✗ | ✓ |
| Zed / Continue | ✗ | ✓ |
| Raw Anthropic/OpenAI API | ✗ (prompt content is usable manually) | ✓ (any MCP client library) |

---

## Troubleshooting

### Skill doesn't appear in `/` completion

- Check `ls ~/.claude/skills/` (user-global) or `ls .claude/skills/` (project-local).
- Confirm YAML frontmatter is valid — the skill fails silently if `---` delimiters are missing or the `name` field is absent.
- Restart the Claude Code session — skills are loaded at session start.

### MCP server doesn't appear in the harness

- Run `terraform-skills-mcp` directly in a terminal — it should print a stdio banner and wait on stdin. If the command is not found, re-run `pip install -e .` from `mcp/`.
- Check the harness's MCP logs. Claude Desktop logs to `~/Library/Logs/Claude/mcp*.log`; Cursor logs to its output panel.
- Confirm the server binary is on the PATH the harness sees — GUI apps often have a different PATH than your shell.

### `tf-test` says "terraform version too old"

Pre-flight requires ≥ 1.6 for native tests and ≥ 1.7 for `mock_provider`. Upgrade, or use the Terratest fallback (section 6 of `tf-test/SKILL.md`).

### `tf-refactor` plan shows unexpected destroys

This is the workflow doing its job. Use `action:triage` — it will localise each destroy to one of: intended, rename/move, provider replace, or state drift. Never apply an unexplained destroy.

### `tf-cost` shows `$0/mo` for real resources

Two likely causes:
1. No `infracost-usage.yml` — usage-based resources (egress, Cloud Logging) need explicit usage estimates.
2. Resource not supported by Infracost — run `infracost breakdown --show-skipped` to confirm.

### Pre-flight demands credentials I don't have

All pre-flights fail closed on purpose. Obtain the relevant credential (GCP SA key, HCP service principal, Infracost API key) before re-running. The workflow will not silently run with partial auth.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the style guide, how to add a new workflow (both shapes), how to test changes, and the PR checklist.

---

## License

Apache-2.0. See [LICENSE](LICENSE).

---

## Related

- [Anthropic — Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [HashiCorp — Terraform native testing](https://developer.hashicorp.com/terraform/language/tests)
- [Infracost](https://www.infracost.io/)
