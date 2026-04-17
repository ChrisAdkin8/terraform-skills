# tf-test

Scaffold and run [Terraform native tests](https://developer.hashicorp.com/terraform/language/tests) (`.tftest.hcl`) with `mock_provider` support. Falls back to Terratest only when explicitly requested.

## Installation

```bash
# from the repo root
./install.sh --target user --only tf-test --mode symlink
```

Or copy `SKILL.md` to `~/.claude/skills/tf-test/SKILL.md` manually.

## Requirements

- Terraform ≥ 1.6 (native `terraform test`)
- Terraform ≥ 1.7 (`mock_provider`, `override_resource`, `override_data`)
- Go ≥ 1.21 **only** if using the Terratest fallback (not the default path)
- `GOOGLE_CREDENTIALS` (apply-mode tests only; plan-mode with mocks needs no cloud creds)

## Arguments

| Key | Values | Default | Purpose |
|---|---|---|---|
| `target` | path | — | Module or scenario under test |
| `action` | `scaffold`, `run`, `discover`, `triage` | `run` if tests exist, else `scaffold` | Which operation |
| `mode` | `plan`, `apply`, `mixed` | `plan` | Execution mode |
| `name` | filename | — | Scope to a single `.tftest.hcl` file |

## Typical usage

```
/tf-test action:scaffold target:tf/modules/vault-pki
/tf-test action:run target:tf/modules/vault-pki
/tf-test action:run target:tf/modules/vault-pki name:defaults.tftest.hcl
/tf-test action:triage target:tf/modules/vault-pki
/tf-test action:run target:tf/scenarios/prod mode:apply
```

## What `action:scaffold` produces

For a new module, the skill scaffolds four baseline test files:

1. **`defaults.tftest.hcl`** — every variable with a default produces the documented resource shape.
2. **`validation.tftest.hcl`** — one `run` per `validation {}` block, using `expect_failures`.
3. **`outputs.tftest.hcl`** — every output is computable at plan time and has the documented shape.
4. **`naming.tftest.hcl`** — resources follow the `{environment}-{component}-{resource}` convention.

For scenarios, adds:

5. **`gate_phase_1.tftest.hcl`** — phase-gated scenarios: no Helm/K8s resources plan when the gate is `false`.

## Composition

See [`../../docs/composition.md`](../../docs/composition.md).

- Pairs with `tf-refactor` — run tests after every state-surgery refactor to catch wrong-address moves.
- Pairs with `tf-cost` — tests should pass before cost is diffed; no point pricing a broken plan.
- Gates `tf-infra action:apply` — a failing plan-mode test should block apply.

Full procedure: [`SKILL.md`](SKILL.md).
