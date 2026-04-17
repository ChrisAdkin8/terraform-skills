# tf-refactor

Safely rename, extract, import, or remove Terraform resources without destroying real infrastructure. Prefers declarative [`moved`](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring), [`import`](https://developer.hashicorp.com/terraform/language/import), and [`removed`](https://developer.hashicorp.com/terraform/language/resources/syntax#removing-resources) blocks over imperative `terraform state` commands.

## Installation

```bash
./install.sh --target user --only tf-refactor --mode symlink
```

## Requirements

- Terraform ≥ 1.1 for `moved` blocks
- Terraform ≥ 1.5 for `import` blocks
- Terraform ≥ 1.7 for `removed` blocks
- Terraform ≥ 1.8 for cross-module `moved`
- Working tree clean (the skill refuses to act on a dirty repo)
- Standard Terraform credentials for the target backend (`GOOGLE_CREDENTIALS`, HCP vars if applicable)

## Arguments

| Key | Values | Purpose |
|---|---|---|
| `target` | path | Directory being refactored |
| `action` | `rename`, `extract`, `import`, `remove`, `for-each`, `triage` | Which refactor |
| `from` | resource address | Source address (required for `rename`, `extract`, `for-each`, `remove`) |
| `to` | resource address | Destination address (required for `rename`, `extract`, `for-each`, `import`) |

## Preference order

The skill enforces this hierarchy for every refactor:

1. `moved` block — always first choice for renames and module extractions.
2. `import` block — always preferred over `terraform import` CLI.
3. `removed` block — always preferred over `terraform state rm`.
4. `terraform state mv/rm` / `terraform import` CLI — last resort, only for things blocks can't express.

## Typical usage

```
# Rename a resource in place
/tf-refactor action:rename target:tf/modules/vault from:google_compute_instance.old to:google_compute_instance.new

# Extract resources into a new module
/tf-refactor action:extract target:tf/scenarios/prod from:google_compute_instance.vault_server[0] to:module.vault.google_compute_instance.server[0]

# Convert count → for_each
/tf-refactor action:for-each target:tf/scenarios/prod from:google_compute_instance.nomad[0] to:google_compute_instance.nomad["nomad-0"]

# Adopt existing infrastructure
/tf-refactor action:import target:tf/modules/logs to:google_storage_bucket.logs

# Stop managing a resource without destroying it
/tf-refactor action:remove target:tf/scenarios/legacy from:google_storage_bucket.legacy_logs

# Investigate unexpected destroys in a plan
/tf-refactor action:triage target:tf/scenarios/prod
```

## Prime directive

**Zero destroys for renames and moves.** A plan that shows `- destroy` where the user expected a move is a failure, regardless of whether the code compiles. The skill verifies this before every apply.

## Pre-flight enforcement

Before any state-touching command, the skill runs:

1. `git status --porcelain` — must be empty.
2. `terraform state pull > state.backup.<timestamp>.tfstate` — keep until apply succeeds.
3. `terraform version` — matches the block types planned.
4. `terraform workspace show` — matches the intended environment.
5. Baseline plan captured for post-refactor comparison.

If any check fails, the skill stops. It will never run with partial preconditions.

## Composition

See [`../../docs/composition.md`](../../docs/composition.md).

- Run `tf-test` after every refactor to catch wrong-address moves.
- Run `tf-cost` afterward — a clean plan should show zero cost delta.
- Feeds `tf-infra action:apply` with a verified refactor-only plan.

Full procedure: [`SKILL.md`](SKILL.md).
