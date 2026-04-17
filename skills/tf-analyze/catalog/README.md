# tf-analyze finding catalogue

Stable finding identifiers used across runs of the skill. Each entry is a single
YAML file. The filename is the canonical ID.

## ID format

```
<DOMAIN>-<SUBDOMAIN>-<NNN>
```

| Domain | Meaning |
|---|---|
| `SEC` | Security |
| `ROB` | Robustness |
| `DRY` | DRY / code reuse |
| `STY` | Style |
| `SIM` | Simplicity |
| `OPS` | Operational readiness |
| `CCD` | CI/CD and testing |
| `MOD` | Cross-module contracts |
| `STK` | Stack-specific (Vault, Consul, GKE, Helm) |
| `VER` | CLAUDE.md verification |

`<SUBDOMAIN>` is a short kebab tag (e.g., `IAM`, `LIFECYCLE`, `LOGGING`). `<NNN>`
is a zero-padded sequence within the subdomain.

**IDs are stable across skill runs and across skill versions.** Once an ID is
allocated it must never be repurposed. Deprecated findings should be marked
`status: deprecated` rather than deleted, so historical reports remain
interpretable.

## Schema

```yaml
id: SEC-IAM-001              # required, must match filename (without .yaml)
title: "Short human title"   # required, ≤80 chars
section: security            # required, one of: security|robustness|dry|style|simplicity|ops|cicd|module|stack|verification
default_urgency: HIGH        # required, one of: CRITICAL|HIGH|MEDIUM|LOW|INFO
blast_radius: module         # required, one of: single-resource|module|environment|infrastructure-wide
status: active               # optional, default active. one of: active|deprecated|experimental
cis:                         # optional, list of CIS GCP v4.0 control IDs
  - "1.6"
patterns:                    # required, ≥1. detection patterns the skill applies.
  - kind: resource_arg       # one of: resource_arg|resource_missing_arg|resource_present|grep|hcl_attr
    resource: google_project_iam_member
    arg: role
    regex: "^roles/(owner|editor|.*Admin)$"
recommendation: |            # required, multiline. recommended fix.
  Replace with `google_storage_bucket_iam_member` (or equivalent
  resource-level binding from Appendix A) and grant the narrowest
  role the workload requires.
verification: |              # required, multiline. how to verify the fix landed.
  After applying the fix, run `terraform plan` and confirm the
  project-level binding is destroyed and the resource-level binding
  is created. Re-run tf-analyze in mode:verify-fixed.
related: []                  # optional, list of related catalogue IDs
escalation:                  # optional, conditions that bump urgency
  - condition: "estimated_monthly_cost_usd > 1000"
    new_urgency: HIGH
fixtures:                    # optional, list of fixture directories that exercise this finding
  - iam_too_broad
```

## Pattern kinds

| Kind | Meaning |
|---|---|
| `resource_arg` | A `resource` block whose argument matches a regex |
| `resource_missing_arg` | A `resource` block of the named type that lacks the named argument |
| `resource_present` | Any `resource` block of the named type triggers the finding |
| `grep` | A regex against the raw file body — last resort, use sparingly |
| `hcl_attr` | A specific HCL nested-block attribute path (e.g., `lifecycle.prevent_destroy`) |

The detection pass walks every `.tf` file in scope, applies every catalogue
pattern, and produces `(file, line, finding_id)` triples. The judgement pass
then assigns urgency (starting from `default_urgency`, applying `escalation`
rules), collapses duplicates, and enriches with context.

## Sequencing within a run

Within a single run, the report assigns instance numbers per finding ID:
`SEC-IAM-001#1`, `SEC-IAM-001#2`, etc. Across runs the catalogue ID is the
stable join key — instance numbers are not.

## Adding a new entry

1. Pick the lowest unused `<NNN>` in the subdomain.
2. Write the YAML file. Validate the schema by running the self-test.
3. Add a fixture under `fixtures/<name>/` that triggers the new pattern.
4. Re-run the skill against the fixture and confirm the new ID surfaces.
5. Reference the new ID from any inline check list in `SKILL.md` that
   produces it (e.g., Step 2b → SEC-IAM-001).
