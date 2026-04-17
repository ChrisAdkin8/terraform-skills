---
name: tf-test
description: Scaffold and run Terraform native tests (`terraform test`, `.tftest.hcl`) and optional Terratest suites for the GCP + HashiCorp stack. Handles test discovery, mock providers, fixture wiring, plan-time vs apply-time assertions, and failure triage. Use when adding tests to a module or scenario, running an existing suite, or debugging a failing test.
argument-hint: "[target:path] [action:scaffold|run|discover|triage] [mode:plan|apply|mixed] [name:test_file]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
model: claude-sonnet-4-6
---

# Terraform Test Assistant

You are adding or running tests for Terraform modules and scenarios on the GCP + HashiCorp stack. Prefer the native `terraform test` runner (HCL-only, no Go toolchain). Fall back to Terratest only when the user explicitly requests it or when coverage requires real post-apply API calls the native runner cannot express.

## Arguments

$ARGUMENTS

Parse from `$ARGUMENTS`:
- `target:PATH` — module or scenario under test (relative or absolute)
- `action:VERB` — `scaffold`, `run`, `discover`, or `triage` (default: `run` if tests exist, else `scaffold`)
- `mode:MODE` — `plan` (fast, no provider credentials), `apply` (real resources), or `mixed` (default: `plan`)
- `name:FILE` — specific `.tftest.hcl` filename to scaffold or run

---

## Step 0: Pre-flight checks

Check the Terraform version — native `terraform test` requires **1.6+**, `mock_provider` requires **1.7+**, and `override_resource`/`override_data` require **1.7+**:

```bash
terraform version
```

If `terraform` < 1.6, stop and tell the user to upgrade. Do not fall back to Terratest silently.

For `mode:apply` runs, validate credentials the same way `tf-infra` does:

```bash
: "${GOOGLE_CREDENTIALS:?Required for apply-mode tests}"
# HCP vars only if the target touches HCP resources
```

For `mode:plan` runs, no cloud credentials are required **if** the test file uses `mock_provider` or `command = plan` with all providers configured to a null/fake endpoint. Confirm this before running.

---

## Step 1: Discover existing tests

```bash
find <TARGET> -name "*.tftest.hcl" -type f
find <TARGET> -path "*/tests/*" -name "*.tf" -type f    # Terratest helpers
find <TARGET> -name "*_test.go" -type f                 # Terratest Go suites
```

Report: test file count, test names (the `run` blocks inside), and whether they are plan-mode or apply-mode. If `action:discover`, stop here and return the inventory.

---

## Step 2: Action — `scaffold`

Tests live in `<TARGET>/tests/` by convention. Filename pattern: `<aspect>.tftest.hcl` (e.g. `defaults.tftest.hcl`, `validation.tftest.hcl`, `outputs.tftest.hcl`).

### Plan-mode test template

Use this for input validation, conditional logic, computed defaults, and output shape. No cloud credentials needed when combined with `mock_provider`.

```hcl
# tests/defaults.tftest.hcl
variables {
  project_id  = "test-project"
  region      = "europe-west2"
  environment = "test"
}

mock_provider "google" {}
mock_provider "google-beta" {}

run "defaults_are_applied" {
  command = plan

  assert {
    condition     = google_compute_instance.this.machine_type == "e2-medium"
    error_message = "Default machine_type drifted from e2-medium"
  }
}

run "rejects_invalid_region" {
  command = plan

  variables {
    region = "not-a-region"
  }

  expect_failures = [var.region]
}
```

### Apply-mode test template

Use sparingly — only for behaviours that require real resource creation (IAM propagation, DNS, certificate issuance). Isolate to an ephemeral project or dedicated test workspace.

```hcl
# tests/integration.tftest.hcl
variables {
  project_id  = "tf-test-ephemeral"
  region      = "europe-west2"
  environment = "test"
}

run "creates_bucket" {
  command = apply

  assert {
    condition     = google_storage_bucket.this.location == "EUROPE-WEST2"
    error_message = "Bucket created in wrong region"
  }
}
```

### What to scaffold (minimum viable coverage)

For a new module test suite, scaffold four files unless the user asks for fewer:

1. `defaults.tftest.hcl` — asserts every variable with a default produces the documented resource shape
2. `validation.tftest.hcl` — one `run` per `validation {}` block, using `expect_failures`
3. `outputs.tftest.hcl` — asserts every output is computable at plan time and has the documented shape
4. `naming.tftest.hcl` — asserts `{environment}-{component}-{resource}` convention (matches `tf-infra` Step 2 rule 3)

For scenarios, also add:

5. `gate_phase_1.tftest.hcl` — asserts no Helm/K8s resources plan when the phase gate is `false` (see `tf-infra` Step 4 phase-gated applies)

### Mocking HashiCorp providers

`vault`, `consul`, `nomad`, and `hcp` providers work with `mock_provider`. For `hcp_vault_cluster` lookups, provide mocked outputs via `override_resource` / `override_data` so downstream computes resolve:

```hcl
mock_provider "hcp" {
  override_data {
    target = data.hcp_vault_cluster.this
    values = {
      vault_public_endpoint_url  = "https://mock.vault.hashicorp.cloud:8200"
      vault_private_endpoint_url = "https://mock-private.vault.hashicorp.cloud:8200"
      namespace                  = "admin"
    }
  }
}
```

---

## Step 3: Action — `run`

```bash
terraform -chdir=<TARGET> init -backend=false
terraform -chdir=<TARGET> test -verbose
```

Flags worth knowing:
- `-filter=tests/<FILE>.tftest.hcl` — run a single file
- `-var-file=<ENV>.tfvars` — seed variables (useful for scenarios that expect env-specific values)
- `-junit-xml=report.xml` — emit JUnit for CI
- `-cloud-run=<workspace>` — run against Terraform Cloud / HCP Terraform

For `mode:plan`, ensure no `command = apply` blocks execute. Run once and confirm every `run` block completed. Any `failed` block → stop and go to Step 5 (triage) before proceeding.

---

## Step 4: Action — `triage`

When a test fails, do not "fix" the test to make it pass. Reproduce → localize → fix the **code** or the **assertion**, whichever is wrong.

Procedure:
1. Re-run the single failing file with `-verbose`:
   ```bash
   terraform -chdir=<TARGET> test -verbose -filter=tests/<FILE>.tftest.hcl
   ```
2. Extract the failing `run` name and the assertion message.
3. Classify the failure:
   - **Assertion wrong** — the code behaviour is correct, the test encoded the wrong expectation. Update the assertion, note why.
   - **Code regression** — the assertion is right; the code changed. Fix the code.
   - **Mock drift** — an `override_data`/`override_resource` no longer matches the real provider shape. Update the mock.
   - **Provider version skew** — the error mentions a field that moved between provider versions. Check `.terraform.lock.hcl`.
4. Add a regression `run` block when fixing code — smallest test that would have caught it.

---

## Step 5: Integration with `tf-infra` and `tf-analyze`

- After `tf-infra action:scaffold` creates a new module, immediately invoke this skill with `action:scaffold target:<new-module>` to create the four baseline test files. A module without tests should be flagged by `tf-analyze` (finding ID in the `robustness` or `ops` catalogue).
- Before `tf-infra action:apply`, run `terraform test` in plan mode as a gate. If any test fails, do not apply.
- The `plan` mode of this skill pairs with `tf-analyze mode:static`; the `apply` mode pairs with `tf-analyze mode:plan`.

---

## Step 6: Terratest fallback (only when explicitly requested)

Use Terratest when:
- The test must call a real cloud API after apply (e.g. actually SSH into a Nomad node, verify Consul service registration end-to-end)
- The user has an existing Go test suite in the repo
- Native `terraform test` cannot express the behaviour (e.g. time-delayed assertions, retry loops)

Layout:
```
tests/
├── go.mod
├── go.sum
└── <module>_test.go
```

Run:
```bash
cd <TARGET>/tests && go test -v -timeout 30m
```

Do not scaffold Terratest by default — the Go toolchain requirement, slower feedback loop, and real-cloud cost make it the wrong default for vibe-coding iteration. Native `terraform test` with `mock_provider` is always the first choice.

---

## Common pitfalls to avoid

- **Don't run apply-mode tests against a shared project.** Use an ephemeral project per run, or a dedicated `terraform-test-*` project with budget alerts.
- **Don't assert on computed attributes in plan mode** — `id`, `self_link`, server-generated timestamps resolve to `(known after apply)` and will fail plan-time assertions. Test those in apply mode or via outputs.
- **Don't commit `.tftest.hcl` files that require real credentials without gating.** Guard with `command = plan` + mocks, or move to a separate `tests-integration/` directory excluded from default `terraform test` runs.
- **Don't use `expect_failures` without specifying the target** — `expect_failures = [var.region]` scopes to a variable; a bare `expect_failures = []` catches everything and hides real bugs.
- **Never mock away the thing under test.** If the module's job is to configure `google_compute_instance`, don't `override_resource` that exact resource — you'll test the mock, not the module.
- **Run `terraform fmt` on `.tftest.hcl` files.** They use HCL and the same formatter; `tf-infra`'s Step 2 formatting rule applies.
- **Phase-gated scenarios need two test files.** One asserts the phase-1 resource set with the gate `false`; one asserts phase-2 additions with the gate `true`. A single test file cannot cover both without re-running init.
