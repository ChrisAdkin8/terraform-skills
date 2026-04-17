# Skill Composition

The four workflows in this repo are independent but designed to compose. The snippets below use the Claude Code slash-command form; the MCP tool names follow the pattern `tf_<workflow>_<action>` — see [`mcp/README.md`](../mcp/README.md) for the full reference. This document shows the intended flows and the hand-off points between them.

## The vibe-coding loop

```
         ┌──────────────┐
         │   author/    │
         │   refactor   │
         └──────┬───────┘
                │
                ▼
      ┌──────────────────┐
      │  tf-refactor     │  ◀──  add moved/import/removed blocks
      │  (state surgery) │       verify zero destroys
      └────────┬─────────┘
               │
               ▼
       ┌──────────────┐
       │   tf-test    │  ◀──  scaffold + run (.tftest.hcl)
       │  (coverage)  │       gate on regressions
       └──────┬───────┘
              │
              ▼
        ┌────────────┐
        │  tf-cost   │  ◀──  diff against current state
        │  (dollars) │       gate on budget
        └─────┬──────┘
              │
              ▼
      ┌───────────────┐
      │   tf-infra    │  ◀──  existing skill: terraform apply
      │  (apply gate) │       shows add/change/destroy + Δ cost
      └───────────────┘
```

## Hand-off points

### `tf-refactor` → `tf-test`

After any refactor, run the test suite to prove behaviour is unchanged. A refactor that passes plan ("0 destroys, moved blocks resolved") but fails a test means the moved block landed on the wrong address, or a downstream reference broke. `tf-test action:run` catches this before apply.

**Contract**: `tf-refactor` leaves the state file backup next to `<TARGET>`. If `tf-test` fails catastrophically (e.g. module unevaluable), that backup is the restore point.

### `tf-test` → `tf-cost`

Tests pass. Now the cost check. The order matters — running cost estimation on a plan that breaks tests is wasted work (you'll change the plan and re-diff).

**Contract**: both skills operate on the same plan file. `tf-test` in `mode:plan` produces no artefact; `tf-cost` regenerates `plan.json` from a fresh `terraform plan`. For long-running plans, cache the `.tfplan` and point both skills at it.

### `tf-cost` → `tf-infra apply`

The cost delta from `tf-cost action:diff` should appear in the apply confirmation prompt. The recommended format:

```
Workspace : prod
Target    : tf/scenarios/vault-hcp
Add       : 3  Change: 1  Destroy: 0
Cost Δ    : +$128.40 /mo  (baseline: $412.60 /mo)

Type 'yes' to apply or anything else to cancel.
```

**Contract**: if `tf-infra` is not installed, invoke the normal `terraform apply` manually. The cost delta is informational — the skills don't block apply automatically; the human does.

## Composing with the broader tf-* ecosystem

These three pair with two existing skills (if you have them):

| Existing skill | Role | Composition point |
|---|---|---|
| `tf-infra` | `init`/`plan`/`apply`/`scaffold` | Apply gate — cost + test results appear in its confirmation prompt. |
| `tf-analyze` | Static/diff/plan-mode analysis, catalog-backed findings | Pre-commit / PR gate. Runs before the refactor-test-cost loop. |

### Full PR flow

```
tf-analyze mode:diff diff-base:main    # posture delta for this branch
tf-refactor action:triage              # explain any destroys in the plan
tf-test action:run                     # regression coverage
tf-cost action:diff                    # dollars delta
tf-cost action:budget threshold:500    # gate on the branch's budget
tf-infra action:apply                  # manual apply with all context surfaced
```

### CI gate flow

Non-interactive variant — each skill has a CI-friendly exit code:

```bash
# .github/workflows/tf-pr.yml or equivalent
- run: terraform -chdir=$TARGET init -backend=false
- run: terraform -chdir=$TARGET test                           # tf-test equivalent
- run: terraform -chdir=$TARGET plan -out=tfplan
- run: terraform -chdir=$TARGET show -json tfplan > plan.json
- run: infracost diff --path plan.json --format json > cost.json
- run: ./ci/check-budget.sh cost.json 500                      # tf-cost budget equivalent
```

The skills do not replace CI — they give a human the same signals faster during authoring. CI runs the same underlying tools.

## Anti-patterns

- **Skipping `tf-refactor` for "simple" renames.** There is no such thing as a simple rename in Terraform state. A one-line name change without a `moved` block destroys and recreates the resource. Always use the skill.
- **Running `tf-test apply`-mode against a real project.** The skill refuses by default for a reason. Apply-mode tests need ephemeral projects or dedicated test environments with budget alerts — configure those before enabling apply-mode tests.
- **Treating `tf-cost` as a security gate.** Cost and security are orthogonal. `tf-analyze` owns posture; `tf-cost` owns dollars. A plan can be secure and expensive, or cheap and insecure.
- **Composing in the wrong order.** `refactor → test → cost → apply` exists for a reason. Cost-before-test wastes work when tests fail. Test-before-refactor misses the state-safety question entirely.
