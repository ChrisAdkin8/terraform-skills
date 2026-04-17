# Changelog

All notable changes to this project are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-04-17

### Added

- `tf-analyze` skill — comprehensive static and plan-time analysis with 60 catalogue-backed finding IDs, 40+ test fixtures, deterministic risk scoring, CIS benchmark mapping, and delta tracking between runs. Execution modes: `static`, `diff`, `plan`, `verify-fixed`, `self-test`. Output formats: `markdown`, `json`, `sarif`.
- `skills/tf-analyze/catalog/` — 60 YAML rule definitions grouped by focus (SEC, ROB, OPS, MOD, COST, CI-TEST) with severity, blast radius, and CIS mapping.
- `skills/tf-analyze/fixtures/` — 40+ synthetic Terraform snippets that assert specific catalogue IDs. Enables `mode:self-test`.
- `skills/tf-analyze/scripts/detect.py` — deterministic detection pass used by `static` and `diff` modes.
- `skills/tf-analyze/integrations/` — drop-in GitHub Actions workflow and pre-commit hook.
- `logo.svg` — repo logo (HCL braces + spark, Terraform purple on dark).
- Top-level `README.md` now embeds the logo and includes `tf-analyze` in the skill table and reference section.
- `install.sh` includes `tf-analyze` in the default skill list.

### Notes

- `skills/tf-analyze/reports/` (dated audit reports against real infrastructure) deliberately excluded from this public release.

## [0.1.0] — 2026-04-17

### Added

- Initial public release.
- `tf-test` skill — scaffold and run Terraform native tests (`.tftest.hcl`) with `mock_provider` support, plus opt-in Terratest fallback. Four-file baseline scaffold (defaults, validation, outputs, naming) with an extra phase-gate file for scenarios.
- `tf-refactor` skill — safe state surgery using `moved` / `import` / `removed` blocks. Actions: `rename`, `extract`, `import`, `remove`, `for-each`, `triage`. Enforces working-tree-clean and state backup pre-flights; verifies zero destroys for rename/move plans.
- `tf-cost` skill — Infracost wrapper. Actions: `baseline`, `diff`, `breakdown`, `budget`. Integrates with `tf-infra`'s apply confirmation to surface monthly cost delta alongside add/change/destroy counts.
- Top-level `README.md` with install options (user-global, project-local, git submodule), prerequisites, skill reference, argument grammar pointer, and troubleshooting.
- `install.sh` installer with `--target {user,project}`, `--mode {symlink,copy}`, `--only <list>`, and `--dry-run` options.
- `CONTRIBUTING.md` with SKILL.md body structure, style rules, PR checklist, reviewer guidance, and versioning policy.
- `docs/composition.md` — how `tf-test`, `tf-refactor`, `tf-cost` compose with each other and with `tf-infra` / `tf-analyze`.
- `docs/argument-grammar.md` — shared `key:value` argument convention across all skills.
- Apache-2.0 license.

[Unreleased]: https://github.com/ChrisAdkin8/claude-skills-terraform/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ChrisAdkin8/claude-skills-terraform/releases/tag/v0.2.0
[0.1.0]: https://github.com/ChrisAdkin8/claude-skills-terraform/releases/tag/v0.1.0
