# Harness compatibility

`terraform-skills` ships in two shapes so it works across AI coding harnesses. This page spells out what each shape gives you, what it doesn't, and how to pick.

## Shape comparison

| Dimension | Claude Code skills (`claude-skills/`) | MCP server (`mcp/`) |
|---|---|---|
| **Works with** | Claude Code only | Any MCP-capable harness (Claude Desktop, Cursor, Cline, Zed, Continue, Claude Code itself, custom clients) |
| **Wire format** | `SKILL.md` — markdown + YAML frontmatter | [Model Context Protocol](https://modelcontextprotocol.io) over stdio/SSE |
| **Invocation** | Slash-command (`/tf-analyze`) or auto-invoke based on `description` | The harness's own tool-calling loop — LLM chooses when to call |
| **Procedure content** | Full playbook embedded in the SKILL.md body (pre-flights, failure modes, integration points, anti-patterns) | None — the server exposes *actions*; procedure lives in the consuming model's prompt |
| **Argument style** | `key:value` grammar parsed from `$ARGUMENTS` by the model | Typed parameters validated by FastMCP from the tool signature |
| **Model selection** | Pinned via frontmatter `model:` field | Whatever model the consuming harness is configured with |
| **Progressive disclosure** | Yes — SKILL.md loads on invocation, not on session start | No — tool schemas are advertised once at connection |
| **Shared assets** | Owns `tf-analyze/catalog/`, `fixtures/`, `scripts/detect.py` | Reads/imports the same assets from `claude-skills/tf-analyze/` |

## What each shape gives you

### Claude skills

- **Opinionated procedure.** The SKILL.md body tells Claude step-by-step how to pre-flight, act, and verify. Good when you want consistent behaviour regardless of which operator invokes it.
- **Auto-invocation.** Claude Code reads every skill's `description` at session start and triggers the right one when the user's ask matches. You get the behaviour without typing the slash command.
- **Playbook for judgement calls.** Example: `tf-refactor` tells Claude to stop if the plan shows a destroy it can't trace to an intent. That judgement *is* the skill.

### MCP server

- **Harness-agnostic.** Same tools across Cursor, Cline, Claude Desktop, Zed, your own agent. No per-harness rewriting.
- **Deterministic actions only.** `tf_analyze(...)` always runs the same `detect.py` the same way. The consuming model decides what to do with the results.
- **Composable with other MCP servers.** Stack it with Filesystem, GitHub, Kubernetes, Vault MCP servers — all from one harness with one config.

## Trade-offs

| If you want… | Pick |
|---|---|
| The richest out-of-the-box experience in Claude Code | Claude skills |
| Portability across harnesses | MCP server |
| Opinionated pre-flights baked in | Claude skills |
| Type-validated tool calls | MCP server |
| Progressive disclosure (skills only load when relevant) | Claude skills |
| Multi-harness team where not everyone uses Claude Code | MCP server (or both) |
| To call workflows from a custom agent / script | MCP server |
| Auto-invocation ("Claude, please…") | Claude skills |

## Running both

Nothing prevents running both surfaces in parallel — they share assets, so they can't drift. Typical setup:

```bash
# Install Claude skills (if you use Claude Code)
./install.sh --target user --mode symlink

# Install MCP server (for other harnesses and for Claude Code's MCP mode)
cd mcp && pip install -e .
```

Then wire the MCP server into whichever harness needs it — see the [top-level README](../README.md#mcp-server) for per-harness config snippets.

## Coverage delta

Every Claude skill has at least one MCP tool equivalent. The delta is in **procedure**, not **capability**:

| Workflow | Claude skill exposes | MCP server exposes |
|---|---|---|
| `tf-analyze` | Full report narrative, delta tracking, verify-fixed prompt flow | `tf_analyze`, `tf_analyze_list_catalog`, `tf_analyze_get_catalog_entry`, `tf_analyze_verify_fixed` |
| `tf-test` | Scaffold-or-run-or-triage decision, Terratest fallback prompting | `tf_test_run`, `tf_test_list`, `tf_test_scaffold` |
| `tf-refactor` | Action router, destroy-triage playbook, state-backup pre-flight | `tf_refactor_plan`, `tf_refactor_generate_moved`, `tf_refactor_generate_import`, `tf_refactor_generate_removed` |
| `tf-cost` | Budget-gate prompting, `infracost-usage.yml` guidance | `tf_cost_breakdown`, `tf_cost_diff`, `tf_cost_budget_check` |

If you run the MCP server from a harness that has no prior knowledge of the workflow, paste the matching `SKILL.md` body into that harness's system prompt or rules file — you get most of the procedural benefit without the invocation contract.
