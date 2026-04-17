# Contributing

Thanks for your interest. This guide covers the style, structure, and review standards for skills in this repo.

## Philosophy

Each skill in this repo embodies three principles:

1. **Safety-first pre-flights.** Skills must fail closed — if credentials, tool versions, or state pre-conditions are missing, stop before any side effect. No silent fallbacks.
2. **Declarative over imperative.** Prefer HCL blocks (`moved`, `import`, `removed`, `mock_provider`) over CLI mutations (`terraform state mv`, `terraform import`). Declarative = reviewable, diffable, survivable across teammates.
3. **Compose, don't overlap.** If a skill needs a capability that another skill owns, call out the composition — don't reimplement. Bigger skills are not better skills.

## Repository layout

```
claude-skills-terraform/
├── README.md                 — top-level user docs
├── LICENSE                   — Apache-2.0
├── CONTRIBUTING.md           — this file
├── CHANGELOG.md              — release notes
├── install.sh                — installer
├── docs/
│   ├── composition.md        — how skills compose
│   └── argument-grammar.md   — shared arg conventions
└── skills/
    ├── tf-test/
    │   ├── README.md         — short, GitHub-browsing friendly
    │   └── SKILL.md          — authoritative skill body (loaded by Claude)
    ├── tf-refactor/
    │   ├── README.md
    │   └── SKILL.md
    └── tf-cost/
        ├── README.md
        └── SKILL.md
```

## Adding a new skill

1. Pick a short, kebab-case name prefixed with `tf-` if Terraform-related. Keep it under 15 chars.
2. Create `skills/<name>/SKILL.md` with the frontmatter template below.
3. Create `skills/<name>/README.md` — short pointer + argument table. Users browsing on GitHub land here first.
4. Add the skill to the top-level `README.md` table and `install.sh`'s default skill list.
5. Add an entry to `CHANGELOG.md` under the "Unreleased" section.
6. Update `docs/composition.md` if the new skill interacts with others.

### `SKILL.md` frontmatter template

```yaml
---
name: tf-<name>
description: >
  One or two sentences explaining what the skill does, when it triggers, and
  the cloud/tooling scope. This field is shown in the `/` completion and
  decides whether Claude auto-invokes the skill — make it precise.
argument-hint: "[key1:value] [key2:value] ..."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
model: claude-sonnet-4-6
---
```

Notes on each field:

- **`name`** — must match the directory name and the `/slash` form.
- **`description`** — first sentence is the `/` completion blurb. Subsequent sentences guide auto-invocation. Keep under ~300 chars.
- **`argument-hint`** — surfaced in the prompt line as the user types. Use the same `key:value` grammar as existing skills.
- **`allowed-tools`** — list only what the skill actually uses. `Agent` should not appear unless the skill genuinely dispatches sub-agents.
- **`model`** — default `claude-sonnet-4-6` for most skills; `claude-opus-4-6` only for heavy analysis skills.

### `SKILL.md` body structure

Existing skills follow this pattern:

1. **Opening paragraph** — one prime directive. What the skill must never violate.
2. **Arguments section** — parse from `$ARGUMENTS` and enumerate accepted keys.
3. **Step 0 — Pre-flight checks** — credentials, tool versions, working tree clean.
4. **Step N — one per action** — the substantive procedure.
5. **Integration section** — how this skill composes with others in the repo.
6. **Stack-specific notes** — HashiCorp-specific / GCP-specific traps.
7. **Common pitfalls to avoid** — bullet list of things that have bitten someone.

Tone: terse, procedural, copy-pasteable commands. Comments inline, not prose paragraphs explaining commands. Every `bash` block must be runnable as-is with placeholder substitution.

## Style rules

- `shell` / `bash` fences use `<TARGET>`, `<ENV>` etc. for placeholders. No angle brackets in prose.
- Prefer tables for argument lists — easier to scan than bullets.
- No emoji.
- No "hope", "probably", "usually" — if the skill is uncertain, the skill has a bug. State preconditions, then act.
- HCL examples must `terraform fmt` cleanly.
- Links between skills use relative paths (`../tf-test/SKILL.md`), not absolute URLs.

## Testing changes

### Manual smoke test

After editing a `SKILL.md`:

1. Install locally with `./install.sh --target user --mode symlink` (symlink so edits propagate).
2. Open Claude Code in a scratch Terraform directory.
3. Run `/tf-<name> action:<each-action>` with minimal arguments.
4. Confirm the pre-flight behaves as documented — especially the fail-closed paths.

### YAML frontmatter validation

```bash
for f in skills/*/SKILL.md; do
  awk '/^---$/{c++; next} c==1' "$f" | head -20
  echo "---"
done
```

Confirm every `name`, `description`, `allowed-tools`, `model` key is present and non-empty.

### HCL examples

If the skill includes HCL in fenced blocks, extract them into a test fixture and run `terraform fmt -check`. See `tf-test` for the pattern.

## Pull request checklist

- [ ] New skill or change follows the `SKILL.md` body structure.
- [ ] Frontmatter passes YAML validation (see above).
- [ ] `README.md` top-level table updated.
- [ ] `install.sh` default list updated (if adding a skill).
- [ ] `CHANGELOG.md` has a new entry under "Unreleased".
- [ ] `docs/composition.md` updated if the skill interacts with others.
- [ ] Smoke-tested locally against a real Terraform directory.
- [ ] No credentials, real project IDs, or internal URLs committed.

## Reviewer guidance

When reviewing a new skill or change, ask:

1. **Does the pre-flight fail closed?** Can the skill cause side effects if a credential is absent?
2. **Is the action list minimal?** Each action should have a distinct pre/post state. Overlapping actions are a sign of unclear scope.
3. **Are the examples realistic?** Copy-paste one and trace it — does it match the repo's documented conventions?
4. **Does it compose cleanly?** A skill that duplicates another's job is a candidate for deletion, not a separate skill.
5. **Is the model right?** Opus is ~5× the cost of Sonnet. Default Sonnet unless the task genuinely needs heavier reasoning.

## Versioning

Semantic versioning at the repo level. A new skill → minor version bump. A breaking change to a skill's argument grammar → major version bump. Prose/typo fixes → patch.

Tag format: `v0.1.0`, `v0.2.0`, etc. Each tag has a corresponding section in `CHANGELOG.md`.
