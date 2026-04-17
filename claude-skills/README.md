# Claude Code skills

The files in this directory are the **Claude-Code-native** surface of `terraform-skills`. Each subdirectory contains a `SKILL.md` file — markdown with YAML frontmatter that Claude Code loads as a pre-baked procedure.

If you are using **Claude Code**, install these directly (see the top-level [README.md](../README.md#claude-code-skills)).

If you are using **any other harness** (Cursor, Cline, Zed, Claude Desktop, raw API, etc.), use the [MCP server](../mcp/) instead — it exposes the same four workflows as Model Context Protocol tools that any MCP-capable client can consume.

## Why two surfaces?

The SKILL.md format is Claude-Code-specific:

- The frontmatter (`allowed-tools`, `argument-hint`, `model`) references Claude Code tool names.
- `$ARGUMENTS` is Claude Code slash-command syntax.
- The body assumes Claude Code's tool set (`Bash`, `Read`, `Glob`, `Grep`, `Write`, `Agent`) and its auto-invocation mechanic.

Other harnesses don't speak that dialect. The MCP server gives them the same *capabilities* — run detection, run test, generate HCL block, estimate cost — in a portable wire format. See [`docs/harness-compatibility.md`](../docs/harness-compatibility.md) for the full comparison.

## Shared assets

These directories are **imported/read by the MCP server**, not duplicated — the two surfaces stay in lockstep by construction:

- `tf-analyze/scripts/detect.py` — deterministic detection pass
- `tf-analyze/catalog/` — 60 YAML rule definitions
- `tf-analyze/fixtures/` — 40+ test fixtures

Editing any of these propagates to both surfaces on next commit.

## Per-skill reference

| Skill | Dir | Purpose |
|---|---|---|
| `tf-analyze` | [`tf-analyze/`](tf-analyze/) | Catalogue-backed static + plan-time analysis |
| `tf-test` | [`tf-test/`](tf-test/) | Scaffold + run `terraform test` |
| `tf-refactor` | [`tf-refactor/`](tf-refactor/) | Safe `moved` / `import` / `removed` state surgery |
| `tf-cost` | [`tf-cost/`](tf-cost/) | Infracost wrapper — baseline, diff, budget |

Installation is handled by the top-level [`install.sh`](../install.sh).
