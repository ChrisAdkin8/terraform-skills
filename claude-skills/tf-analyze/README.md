# tf-analyze

Comprehensive static and plan-time analysis of Terraform code with catalogue-backed findings, deterministic risk scoring, CIS benchmark mapping, and delta tracking between runs. GCP-first, AWS/Azure secondary.

## Installation

```bash
# from the repo root
./install.sh --target user --only tf-analyze --mode symlink
```

## Requirements

- Claude Code (the skill body runs inside a Claude session)
- Terraform ≥ 1.1 for static analysis; ≥ 1.5 for `mode:plan` plan-time findings
- Python ≥ 3.10 for `scripts/detect.py` (the deterministic detection pass)
- Git (for `mode:diff` base-branch detection)
- Cloud credentials only when using `mode:plan` (backend access for real plans)

## Arguments

| Key | Values | Default | Purpose |
|---|---|---|---|
| `path` | directory | repo root | Scope analysis to a specific path |
| `focus` | `security`, `dry`, `style`, `robustness`, `simplicity`, `ops`, `cicd`, `all` | `all` | Limit to one area |
| `format` | `markdown`, `json`, `sarif` | `markdown` | Output format. SARIF annotates CI (GitHub Actions, Azure DevOps). |
| `mode` | `static`, `diff`, `plan`, `verify-fixed`, `self-test` | `static` | Execution mode — see below |
| `diff-base` | git ref | auto (`main`/`master`) | Base branch for `mode:diff` |

## Execution modes

| Mode | Cost | Credentials | Output | When |
|---|---|---|---|---|
| `static` | ~5 min | No | Full report | First audit, post-refactor sanity check |
| `diff` | ~1 min | No | Changed files only | PR review, CI gating |
| `plan` | ~15 min | Yes | Full + plan-time findings | Drift suspicion, destroy-recreate detection |
| `verify-fixed` | ~1 min | No | Verification report | Confirm a previous report's findings are resolved |
| `self-test` | ~2 min | No | Pass/fail per fixture | After editing the catalogue or skill body |

## Typical usage

```
/tf-analyze                                       # full static audit, markdown output
/tf-analyze mode:diff                             # PR gate — changed files only
/tf-analyze path:tf/scenarios/prod focus:security
/tf-analyze mode:plan path:tf/scenarios/prod      # with real plan
/tf-analyze format:sarif                          # for CI annotation
/tf-analyze mode:self-test                        # after editing the catalogue
```

## Repository layout

```
skills/tf-analyze/
├── SKILL.md               — authoritative skill body
├── catalog/               — 60 YAML rule definitions + catalogue README
├── fixtures/              — 40+ synthetic Terraform snippets that assert specific catalogue IDs
├── scripts/
│   ├── detect.py          — deterministic detection pass (static + diff modes)
│   └── self_test.py       — asserts fixtures produce their declared IDs
└── integrations/
    ├── github-action.yml  — drop-in GitHub Actions workflow
    ├── pre-commit-hook.yaml — pre-commit integration
    └── README.md
```

## Catalogue

Findings have stable IDs grouped by focus area:

- `SEC-*` — security posture (IAM, buckets, logging, network, providers)
- `ROB-*` — robustness (validation, backend, provider alias, lifecycle, moved blocks, versions, counts)
- `OPS-*` — operational readiness (labels, environment tags)
- `MOD-*` — module hygiene (pinning)
- `COST-*` — cost risk signals
- `CI-TEST-*` — CI/CD maturity

Each catalogue entry declares the rule description, severity, blast radius, CIS benchmark mapping, and the fixture(s) that exercise it. Adding a finding means adding a YAML entry **and** a fixture; `mode:self-test` enforces the pairing.

## CI integration

See [`integrations/README.md`](integrations/README.md) for the GitHub Actions workflow and pre-commit hook.

SARIF output (`format:sarif`) annotates PRs with findings at the exact line — no separate reporting dashboard required. Pairs with GitHub Code Scanning.

## Composition

See [`../../docs/composition.md`](../../docs/composition.md).

- Runs **before** the refactor/test/cost loop — posture issues surfaced here inform what the refactor should address.
- Pairs with `tf-cost` — security and cost are orthogonal; both gate apply.
- Complements `tf-infra` — catches issues the apply-path doesn't check.

Full procedure and step-by-step execution: [`SKILL.md`](SKILL.md).
