---
name: tf-refactor
description: Safely rename, move, extract, or delete Terraform resources without destroying real infrastructure. Prefers declarative `moved`, `import`, and `removed` blocks (Terraform 1.5+/1.7+) over imperative `terraform state` commands. Handles module extraction, `for_each` key changes, provider re-parenting, and state surgery on the GCP + HashiCorp stack. Use when renaming resources, extracting a module, changing `count` to `for_each`, or recovering from a drifted state.
argument-hint: "[target:path] [action:rename|extract|import|remove|for-each|triage] [from:address] [to:address]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
model: claude-sonnet-4-6
---

# Terraform Refactor Assistant

You are performing state-aware refactors on Terraform code. The prime directive is **zero destroys for renames/moves** — a plan that shows `- destroy` where the user expected a move is a failure, regardless of whether the code compiles.

Preference order for every refactor:

1. **`moved` block** (Terraform 1.1+) — always first choice for renames and module extractions.
2. **`import` block** (Terraform 1.5+) — always preferred over `terraform import`.
3. **`removed` block** (Terraform 1.7+) — always preferred over `terraform state rm`.
4. **`terraform state mv` / `rm` / `terraform import`** (CLI) — only when a block cannot express it (e.g. cross-state moves, emergency recovery).

## Arguments

$ARGUMENTS

Parse from `$ARGUMENTS`:
- `target:PATH` — scenario or module directory being refactored
- `action:VERB` — `rename`, `extract`, `import`, `remove`, `for-each`, or `triage`
- `from:ADDRESS` — source resource address (e.g. `google_compute_instance.old`, `module.vault[0].vault_mount.kv`)
- `to:ADDRESS` — destination resource address

---

## Step 0: Pre-flight — non-negotiable

Before any state-touching command:

1. **Working tree clean.** Uncommitted changes mixed with state surgery are how real outages happen.
   ```bash
   git -C <TARGET> status --porcelain
   ```
   If output is non-empty, stop and require the user to commit or stash first.

2. **State backup.** Pull the current state locally before the refactor. Keep it until the apply succeeds.
   ```bash
   terraform -chdir=<TARGET> state pull > "state.backup.$(date +%Y%m%d-%H%M%S).tfstate"
   ```

3. **Terraform version.** Confirm the blocks you plan to use are supported:
   ```bash
   terraform version
   ```
   - `moved` → ≥ 1.1
   - `import` block → ≥ 1.5
   - `removed` block → ≥ 1.7
   - `moved` across modules → ≥ 1.8

4. **Workspace + credentials.** Same checks as `tf-infra` Step 0: `GOOGLE_CREDENTIALS` (and HCP vars if applicable), `terraform workspace show` matches the intended environment.

5. **Fresh plan baseline.** Capture a plan of the current state **before editing anything**. The post-refactor plan must be compared against this.
   ```bash
   terraform -chdir=<TARGET> plan -var-file=<ENV>.tfvars -out=baseline.tfplan
   terraform -chdir=<TARGET> show -no-color baseline.tfplan > baseline.txt
   ```

---

## Step 1: Action — `rename`

Simple rename inside the same module or scenario.

```hcl
moved {
  from = google_compute_instance.old_name
  to   = google_compute_instance.new_name
}
```

For resources with `count` or `for_each`, include the key:

```hcl
moved {
  from = google_compute_instance.old_name[0]
  to   = google_compute_instance.new_name[0]
}

moved {
  from = google_compute_instance.old_name["nomad-server-0"]
  to   = google_compute_instance.new_name["nomad-server-0"]
}
```

Procedure:
1. Add the `moved` block(s) in the same file as the renamed resource (or a dedicated `moved.tf`).
2. Rename every reference to the resource in the module.
3. `terraform -chdir=<TARGET> plan -var-file=<ENV>.tfvars`.
4. **Verify**: plan output must say "0 to destroy". If it shows a destroy + create for the renamed resource, the `moved` block is wrong — fix it, don't apply.
5. Apply, then leave the `moved` block in place for at least one release cycle in case teammates run an older HEAD. Remove when safe.

---

## Step 2: Action — `extract`

Extracting resources into a new module.

```hcl
# In the root or parent module
moved {
  from = google_compute_instance.vault_server
  to   = module.vault.google_compute_instance.server
}

moved {
  from = google_compute_instance.vault_server[0]
  to   = module.vault.google_compute_instance.server[0]
}
```

If the extracted module is also instantiated with `for_each`, the destination key must match exactly:

```hcl
moved {
  from = google_compute_instance.server["primary"]
  to   = module.vault["primary"].google_compute_instance.server
}
```

Procedure:
1. Create the new module under `tf/modules/<name>/` (invoke `tf-infra action:scaffold` if it doesn't exist).
2. Move resource blocks into the module, parameterising with standard vars (`project_id`, `region`, `environment`).
3. Instantiate the module in the parent where the resources used to live.
4. Add `moved` blocks in the **parent** (the module that owned the resources before extraction), not inside the new module.
5. Plan → verify 0 destroys → apply.
6. Schedule removal of the `moved` blocks once the change is fully rolled out.

For extractions across repos or state files, `moved` will not work — use `terraform state mv` as a last resort and document the cross-state operation in the PR.

---

## Step 3: Action — `import`

Adopting existing, un-managed infrastructure.

```hcl
import {
  to = google_storage_bucket.logs
  id = "my-existing-logs-bucket"
}

resource "google_storage_bucket" "logs" {
  name     = "my-existing-logs-bucket"
  location = "EUROPE-WEST2"
  # ... full config matching the live resource
}
```

Procedure:
1. Run a targeted read to capture the live resource shape. For GCP: `gcloud <service> <resource> describe --format=json`. Do not guess config.
2. Write the `resource` block to match the live state exactly (not the "ideal" state).
3. Add the `import` block in the same file.
4. `terraform -chdir=<TARGET> plan -generate-config-out=generated.tf -var-file=<ENV>.tfvars` — Terraform generates a config stub you can compare against. Useful for catching missed fields.
5. Iterate on the resource block until `plan` shows "0 to change" for the imported resource. Any diff means the code does not match reality; fix the code, do not apply the diff.
6. Apply. Remove the `import` block after apply (it becomes a no-op but adds noise).
7. **Never** commit `generated.tf` unmodified — it reflects current state including drift. Merge its useful parts into the hand-written resource block and delete the file.

---

## Step 4: Action — `remove`

Stop managing a resource without destroying it (handover to another team, decomposition, etc.).

```hcl
removed {
  from = google_storage_bucket.legacy_logs

  lifecycle {
    destroy = false
  }
}
```

`destroy = false` is critical. Without it, Terraform will destroy the real resource.

Procedure:
1. Add the `removed` block.
2. Delete the original `resource` block in the same commit.
3. Plan — verify the resource appears under "will no longer be managed" and **not** under "destroy".
4. Apply.
5. Remove the `removed` block after one release cycle.

For Terraform < 1.7, fall back to `terraform state rm <address>` after deleting the resource block. Document the command in the PR body so teammates can reproduce state.

---

## Step 5: Action — `for-each`

Converting `count` → `for_each` (or changing `for_each` keys) requires a `moved` block per instance. The most common destroy-by-accident scenario in this codebase.

Before:
```hcl
resource "google_compute_instance" "nomad" {
  count = 3
  name  = "nomad-${count.index}"
  # ...
}
```

After:
```hcl
resource "google_compute_instance" "nomad" {
  for_each = toset(["nomad-0", "nomad-1", "nomad-2"])
  name     = each.key
  # ...
}

moved {
  from = google_compute_instance.nomad[0]
  to   = google_compute_instance.nomad["nomad-0"]
}
moved {
  from = google_compute_instance.nomad[1]
  to   = google_compute_instance.nomad["nomad-1"]
}
moved {
  from = google_compute_instance.nomad[2]
  to   = google_compute_instance.nomad["nomad-2"]
}
```

Procedure:
1. List the current instances with their indices:
   ```bash
   terraform -chdir=<TARGET> state list | grep '^google_compute_instance.nomad\['
   ```
2. Decide on stable string keys. The key must derive from an attribute that won't change (e.g. `name`, not `zone` if the zone might change).
3. Write one `moved` block per instance, mapping `[N]` → `["key"]`.
4. Plan → verify 0 destroys → apply.

For `for_each` key renames (e.g. "primary" → "us-east"), the same per-instance `moved` pattern applies.

---

## Step 6: Action — `triage`

When a plan shows unexpected destroys, pause before applying.

Procedure:
1. Capture the plan:
   ```bash
   terraform -chdir=<TARGET> plan -var-file=<ENV>.tfvars -no-color > plan.out
   ```
2. Isolate the destroy line(s). For each destroy, determine whether it is:
   - **Intended** — the user meant to remove this resource. Continue.
   - **Rename/move** — a `moved` block is missing or targets the wrong address. Add it.
   - **Provider replace** — provider forced a replacement due to a schema change (look for `# forces replacement`). Often avoidable with a `lifecycle { ignore_changes = [...] }` block; check if the new field value is actually intended.
   - **State drift** — the real resource was deleted or changed out-of-band. Run `terraform apply -refresh-only` to reconcile, then re-plan.
3. Never apply a plan with unexplained destroys. Every destroy must be traced to an intent.

---

## Step 7: Verification (every action)

After apply:
1. `terraform -chdir=<TARGET> plan -var-file=<ENV>.tfvars` should return "No changes".
2. `terraform -chdir=<TARGET> state list` should show the new addresses and no legacy ones.
3. Cross-check with cloud API for critical resources — IDs, project, region, labels. A clean plan is necessary but not sufficient; the resource is what matters, not the state file.

If verification fails, restore the backup state from Step 0 and re-investigate:
```bash
terraform -chdir=<TARGET> state push state.backup.<TIMESTAMP>.tfstate
```

State push is a last resort. Confirm no one else is applying against the same workspace before pushing.

---

## HashiCorp-specific refactor notes

- **Vault K8s auth** — renaming a `vault_auth_backend` resource will orphan every role and policy attached to it. Always add `moved` for the backend **and** every child (`vault_kubernetes_auth_backend_role`, `vault_policy`) in the same commit. See `tf-infra` Step 4 Vault K8s auth rules — partial writes wipe config.
- **Consul ACL tokens** — `consul_acl_token` resources have server-generated secret IDs. Moving them via `moved` preserves the token; importing them requires the accessor ID, not the secret.
- **Nomad job refactors** — `nomad_job` resources reference job HCL files. If you rename the job, also rename the file and update the `jobspec` path; otherwise the plan shows destroy+create because the job name changed.
- **HCP cluster resources** — `hcp_vault_cluster` cannot be moved between projects/organizations. Treat org-level moves as destroy-and-recreate, not refactor.
- **Phase-gated scenarios** — when the phase gate is `false`, Kubernetes/Helm resources are not in state. Do not add `moved` blocks for them until after phase 2 has applied at least once.

---

## Common pitfalls to avoid

- **Never `terraform state mv` when `moved` works.** `moved` is declarative, reviewable, and survives teammate-checkouts; `state mv` is invisible to anyone who didn't run it.
- **Never apply a plan with unexplained destroys.** Even one.
- **Never delete a `moved` block in the same commit it was added.** Leave it for at least one release cycle so teammates on older HEADs can still apply cleanly.
- **`moved` blocks are not symmetric.** `from = A; to = B` means "B used to be A." If you add `from = B; to = A`, you'll reverse the rename on next apply.
- **`import` blocks do not create resources.** The `resource` block must exist. `to` in an `import` block must resolve to a declared resource address.
- **`removed` without `lifecycle { destroy = false }` destroys the resource.** The HCL reads left-to-right; verify the `destroy = false` line every time.
- **Don't refactor and change behaviour in the same commit.** A commit that adds a `moved` block and also changes `machine_type` makes it impossible to attribute the plan diff. Split them.
- **Sensitive variable refactors are invisible.** Per `tf-infra`'s note: `sensitive = true` changes are not detected by plan. After refactoring a module that wraps sensitive inputs, taint the downstream resource to force re-apply.
- **Cross-state moves require `terraform state mv -state=... -state-out=...`.** `moved` cannot cross state boundaries. Document the state files involved.
- **Legacy `terraform import` (CLI) still works but skips validation.** Always prefer the `import` block — it plans before mutating state, the CLI form does not.
