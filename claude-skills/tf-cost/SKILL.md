---
name: tf-cost
description: Estimate Terraform infrastructure cost, generate pre-apply cost diffs, and enforce budget gates for the GCP + HashiCorp stack. Wraps Infracost to show baseline monthly cost, plan-time delta, per-resource breakdown, and budget threshold checks. Use before applying a non-trivial plan, during module authoring to compare design options, or when investigating why a scenario got expensive.
argument-hint: "[target:path] [action:baseline|diff|breakdown|budget] [env:dev|staging|prod] [threshold:USD] [format:table|json|html]"
allowed-tools: Bash, Read, Write, Glob, Grep
model: claude-sonnet-4-6
---

# Terraform Cost Assistant

You are estimating and gating infrastructure cost for Terraform scenarios on the GCP + HashiCorp stack. Use Infracost as the primary engine — it is free for open data, supports GCP/AWS/Azure + HashiCorp Cloud Platform SKUs, and integrates cleanly with `terraform plan` output.

The prime directive is **never let the user apply an unreviewed cost delta**. An unexpected `$5k/month` NAT gateway or `hcp_vault_cluster` tier upgrade should be caught here, not on the bill.

## Arguments

$ARGUMENTS

Parse from `$ARGUMENTS`:
- `target:PATH` — scenario or module to estimate
- `action:VERB` — `baseline`, `diff`, `breakdown`, or `budget` (default: `diff` if a plan file exists, else `baseline`)
- `env:NAME` — environment (used to pick the tfvars file; default: `dev`)
- `threshold:USD` — monthly cost ceiling for `action:budget` (e.g. `threshold:500`)
- `format:MODE` — `table` (default), `json`, or `html`

---

## Step 0: Pre-flight

1. **Infracost installed:**
   ```bash
   command -v infracost || { echo "Install: brew install infracost"; exit 1; }
   infracost --version
   ```

2. **API key configured:**
   ```bash
   : "${INFRACOST_API_KEY:?Run 'infracost auth login' or export INFRACOST_API_KEY}"
   ```
   If not set, run `infracost auth login` (free tier) and note the key in the user's shell profile.

3. **Terraform credentials** for generating plan JSON — same as `tf-infra` Step 0: `GOOGLE_CREDENTIALS`, and HCP vars if the target touches HCP resources. Cost estimation runs against a plan file, which requires `terraform plan` to succeed.

4. **Target directory has a plan.** Infracost needs either:
   - A plan JSON: `terraform show -json tfplan > plan.json`
   - Or a Terraform directory it can init/plan itself (slower, and requires credentials in the Infracost subprocess).

   Prefer the plan JSON path — faster and decouples cost estimation from Terraform version/provider auth.

5. **Usage file (optional but recommended).** Many GCP resources (egress, Cloud Logging ingestion, Cloud Run invocations) have usage-based pricing Infracost cannot infer from config alone. Check for `<TARGET>/infracost-usage.yml`; if absent, generate a template:
   ```bash
   infracost breakdown --path <TARGET> --sync-usage-file --usage-file <TARGET>/infracost-usage.yml
   ```
   Commit the usage file alongside the tfvars.

---

## Step 1: Action — `baseline`

Show current-state monthly cost of the target as-is (no plan diff).

```bash
terraform -chdir=<TARGET> init
terraform -chdir=<TARGET> plan -var-file=<ENV>.tfvars -out=tfplan
terraform -chdir=<TARGET> show -json tfplan > plan.json

infracost breakdown \
  --path plan.json \
  --usage-file <TARGET>/infracost-usage.yml \
  --format <FORMAT>
```

Report:
- **Monthly cost** (total)
- **Top 5 resources by cost** — these are where design attention pays off
- **Resources with `$0/mo`** — either free-tier, usage-based with no estimate, or not supported by Infracost. Flag unsupported resources explicitly; they are blind spots.
- **Hourly vs monthly breakdown** — some resources (spot VMs, HCP dev-tier clusters) have very different optics hourly vs monthly.

---

## Step 2: Action — `diff`

Compute the cost delta between the current state and the proposed plan. This is the default mode and the one you should run before every non-trivial apply.

```bash
# Plan against a zero-state reference (current infrastructure)
terraform -chdir=<TARGET> plan -var-file=<ENV>.tfvars -out=tfplan
terraform -chdir=<TARGET> show -json tfplan > plan.json

infracost diff \
  --path plan.json \
  --usage-file <TARGET>/infracost-usage.yml \
  --format <FORMAT>
```

Infracost's `diff` output shows:
- `+$X/mo` per added/upgraded resource
- `-$X/mo` per removed/downgraded resource
- Net monthly change

Interpretation rules:
- **Net delta > $100/mo and not in a PR description** → stop and ask the user to confirm the scope before apply.
- **Any single resource > $500/mo appearing new** → flag with resource name, SKU/tier, and likely cause (region misconfig, default machine type, HCP tier bump).
- **Sudden drop without matching destroy** → usage file mismatch, not a real saving. Re-sync usage before trusting.
- **Unsupported resource list grows** → the diff is incomplete; note it in the report.

---

## Step 3: Action — `breakdown`

Detailed per-resource table. Use when baseline or diff flags a surprise and you need to localise which block is responsible.

```bash
infracost breakdown \
  --path plan.json \
  --usage-file <TARGET>/infracost-usage.yml \
  --show-skipped \
  --format table
```

`--show-skipped` is important — it lists resources Infracost could not price. If the user's concern maps to a skipped resource (e.g. `consul_acl_policy`, `vault_mount`), state plainly that the cost is not estimated and point to where to look (Consul ENT licence, Vault ENT licence, egress).

For JSON output (CI integration, custom dashboards):
```bash
infracost breakdown --path plan.json --format json > cost.json
jq '.projects[0].breakdown.resources[] | {name, monthlyCost, costComponents: [.costComponents[].name]}' cost.json
```

---

## Step 4: Action — `budget`

Enforce a monthly cost ceiling. Fails non-zero if the plan exceeds `threshold:USD`. Intended for CI gates and pre-apply confirmation.

```bash
infracost breakdown \
  --path plan.json \
  --usage-file <TARGET>/infracost-usage.yml \
  --format json > cost.json

TOTAL=$(jq -r '.totalMonthlyCost' cost.json)
THRESHOLD=<THRESHOLD>

awk -v total="$TOTAL" -v limit="$THRESHOLD" \
  'BEGIN { if (total+0 > limit+0) { printf "FAIL: $%.2f/mo > $%.2f/mo budget\n", total, limit; exit 1 } else { printf "OK: $%.2f/mo <= $%.2f/mo budget\n", total, limit } }'
```

Report the total, the threshold, and the top three contributors when over budget. Do not auto-"fix" by recommending tier downgrades — surface the facts and let the user decide.

---

## Step 5: Integration with `tf-infra`, `tf-test`, and `tf-analyze`

- **Gate `tf-infra action:apply`**: run `action:diff` after the plan and before the confirmation prompt. Include the monthly delta in the confirmation block alongside add/change/destroy counts:
  ```
  Workspace : <ENV>
  Target    : <TARGET>
  Add       : N  Change: N  Destroy: N
  Cost Δ    : +$XXX.XX /mo (baseline: $YYY.YY /mo)

  Type 'yes' to apply or anything else to cancel.
  ```
- **CI gate**: run `action:budget` with env-specific thresholds (`dev`: low, `prod`: higher). Failing the gate fails the CI job.
- **Module authoring**: when comparing two design options, run `action:baseline` against each and diff them. A `db-n1-standard-4` vs `db-custom-2-4096` comparison is 30 seconds, not a support ticket.
- **Not a security scan**: `tf-analyze` covers misconfigurations; `tf-cost` covers bill surprises. Both should run before apply.

---

## HashiCorp-specific cost traps

- **HCP Vault cluster tiers** — `dev` is ~$0.50/hr, `starter_small` is ~$1.58/hr, `standard_small` is ~$1.58/hr, `plus_small` is ~$5.44/hr (check Infracost for current rates; tiers and prices change). Tier upgrades are a one-line change with a ~10× cost impact. Always flag.
- **HCP Consul** — similar tier stratification; dev clusters are non-HA and not suitable for prod but priced accordingly.
- **Self-hosted Vault/Consul/Nomad on GCE** — the licence cost is not captured by Infracost. Note explicitly: "Infracost shows compute only; ENT licensing not included."
- **Vault dynamic GCP credentials** — each `impersonated_account` role potentially creates service accounts. Free per-SA, but IAM policy propagation adds small operational cost.
- **Nomad client fleets with autoscaling** — the cost depends on the autoscaler policy, not the Terraform config. Usage file must specify the expected steady-state node count.

## GCP-specific cost traps

- **NAT Gateway** — ~$45/mo baseline + per-GB egress. Scenarios with one NAT per AZ quietly triple.
- **GKE Autopilot vs Standard** — Autopilot charges per pod-second; a small workload can be cheaper, a large one much more expensive. Compare explicitly.
- **Persistent Disk SSD vs HDD** — default machine-type changes silently switch between them at higher sizes.
- **Egress between regions** — `us-central1` → `europe-west2` traffic is billed; Infracost needs the usage file to price it.
- **Cloud Logging / Monitoring ingestion** — usage-based; easy to exceed free tier in noisy scenarios. Usage file estimates required.
- **Load balancers** — each forwarding rule is ~$18/mo minimum; a phase-gated scenario creating multiple during phase 2 produces a step change that `diff` will catch.

---

## Common pitfalls to avoid

- **Don't trust a diff without a usage file** for any project that has usage-based resources. The diff will underestimate.
- **Don't run Infracost against `.tfstate`** — prices from state reflect last-applied config, not proposed changes. Use a plan JSON.
- **Don't report `$0/mo` as "free"** — it often means "not supported by the pricing engine". Check `--show-skipped`.
- **Don't commit `plan.json`** — it contains resolved variable values including potential secrets. Add to `.gitignore`.
- **Do commit `infracost-usage.yml`** — it is reviewable, versionable, and the source of truth for usage assumptions.
- **Don't use this as a security gate.** Cost and security are orthogonal; `tf-analyze` owns security.
- **Don't block on `$5/mo` diffs** — the point is to catch order-of-magnitude surprises. Tune CI thresholds so noise doesn't erode trust in the gate.
- **HCP tier changes are small diffs in HCL, large diffs in dollars.** Always re-run `action:diff` after any change to `hcp_vault_cluster` or `hcp_consul_cluster` tier/size.
- **Multi-environment scenarios need per-env thresholds.** `prod` budget > `dev` budget by a wide margin; a single shared threshold is either too tight for prod or too loose for dev.
