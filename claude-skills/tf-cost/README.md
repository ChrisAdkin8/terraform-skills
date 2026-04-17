# tf-cost

Estimate monthly infrastructure cost, generate pre-apply cost diffs, and enforce budget gates. Wraps [Infracost](https://www.infracost.io/).

## Installation

```bash
./install.sh --target user --only tf-cost --mode symlink
```

## Requirements

- [Infracost](https://www.infracost.io/docs/#quick-start) ≥ 0.10 — `brew install infracost` on macOS
- `INFRACOST_API_KEY` env var — free tier, obtain via `infracost auth login`
- Standard Terraform credentials for the target (`GOOGLE_CREDENTIALS`, HCP vars if applicable) — needed to generate the plan JSON
- Optional: `<TARGET>/infracost-usage.yml` — required for accurate pricing of usage-based resources (egress, Cloud Logging, Cloud Run)

## Arguments

| Key | Values | Default | Purpose |
|---|---|---|---|
| `target` | path | — | Scenario or module to estimate |
| `action` | `baseline`, `diff`, `breakdown`, `budget` | `diff` if plan exists, else `baseline` | Operation |
| `env` | `dev`, `staging`, `prod` | `dev` | Selects tfvars file |
| `threshold` | USD (number) | — (required for `budget`) | Monthly ceiling |
| `format` | `table`, `json`, `html` | `table` | Output format |

## Typical usage

```
# Current-state monthly cost
/tf-cost action:baseline target:tf/scenarios/prod env:prod

# Cost delta for the next apply
/tf-cost action:diff target:tf/scenarios/prod env:prod

# Per-resource breakdown (with skipped resources flagged)
/tf-cost action:breakdown target:tf/scenarios/prod env:prod format:json

# CI budget gate
/tf-cost action:budget target:tf/scenarios/prod env:prod threshold:500
```

## What gets flagged

| Condition | Flag |
|---|---|
| Net monthly delta > $100 and not in the PR description | Stop-and-confirm before apply |
| Any new single resource > $500/mo | Name + SKU/tier + likely cause (region misconfig, default machine type, HCP tier bump) |
| Sudden drop without matching destroy | Usage file mismatch, not a real saving — re-sync before trusting |
| Unsupported resource list grows | Diff is incomplete — note in the report |

## HashiCorp-specific traps

- **HCP Vault tier changes** — `dev` → `plus_small` is a one-line HCL change with ~10× monthly cost impact. Always flagged.
- **Self-hosted Vault/Consul/Nomad ENT licences** — Infracost does not capture these. The skill explicitly notes "Infracost shows compute only; ENT licensing not included."
- **Nomad client fleets with autoscaling** — cost depends on autoscaler policy, not Terraform config. The usage file must specify expected steady-state node count.

## GCP-specific traps

- **NAT Gateway** — ~$45/mo baseline + per-GB egress. Scenarios with one NAT per AZ quietly triple.
- **GKE Autopilot vs Standard** — pricing models differ; compare explicitly.
- **Load balancers** — each forwarding rule is ~$18/mo minimum; phase-gated scenarios creating multiple in phase 2 produce a step change `diff` will catch.

## Composition

See [`../../docs/composition.md`](../../docs/composition.md).

- Runs **after** `tf-test` in the vibe-coding loop — no point pricing a broken plan.
- Feeds `tf-infra action:apply` with a `Cost Δ` line in the confirmation prompt.
- Complements `tf-analyze` — cost and security are orthogonal; both gate apply.

## Not a security scan

Cost and security are different concerns. `tf-analyze` owns security posture. `tf-cost` owns dollars. A plan can be secure and expensive, or cheap and insecure. Run both.

Full procedure: [`SKILL.md`](SKILL.md).
