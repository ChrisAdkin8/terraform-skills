# Argument Grammar

All skills in this repo share a `key:value` argument convention. This document is the spec.

## Basic form

```
/tf-<skill> key1:value1 key2:value2 ...
```

- Keys and values are separated by a colon (`:`), **no spaces** around it.
- Multiple `key:value` pairs are whitespace-separated.
- Order does not matter — pairs are parsed into a map.

Example:

```
/tf-refactor target:tf/modules/vault action:rename from:google_compute_instance.old to:google_compute_instance.new
```

is equivalent to:

```
/tf-refactor action:rename to:google_compute_instance.new from:google_compute_instance.old target:tf/modules/vault
```

## Quoting values

Values containing spaces, colons, or shell metacharacters must be quoted with double quotes:

```
/tf-test target:"tf/scenarios/my scenario" name:"defaults (baseline).tftest.hcl"
```

Inside quoted values, a literal double quote is escaped with a backslash: `\"`.

Values that are themselves Terraform resource addresses and contain brackets (`[0]`, `["key"]`) do **not** need quoting because brackets are not shell-significant:

```
/tf-refactor action:for-each from:google_compute_instance.nomad[0] to:google_compute_instance.nomad["nomad-0"]
```

## Shared keys

These keys have consistent semantics across every skill that accepts them:

| Key | Value type | Meaning |
|---|---|---|
| `target` | path | Module or scenario directory. Relative to the repo root or absolute. |
| `env` | `dev`, `staging`, `prod`, or custom | Environment name. Selects tfvars file and workspace. Default: `dev`. |
| `action` | verb | Which sub-action to run. Each skill defines its own verb set. |
| `format` | `table`, `json`, `markdown`, `html`, `sarif` | Output format. Skill-dependent subset. |
| `from` | resource address | Source address for moves, imports, renames. |
| `to` | resource address | Destination address. |

## Skill-specific keys

| Skill | Key | Value type | Meaning |
|---|---|---|---|
| `tf-test` | `mode` | `plan`, `apply`, `mixed` | Execution mode. Default: `plan`. |
| `tf-test` | `name` | filename | Specific `.tftest.hcl` file to scaffold or run. |
| `tf-cost` | `threshold` | USD (number) | Monthly budget ceiling for `action:budget`. |
| `tf-refactor` | (uses shared keys only) | — | — |

## Defaults and omissions

Every key has a documented default in the skill body. Omitting a key is equivalent to passing the default value. A skill will never fail with "missing argument" for a key that has a default — it will use the default and note it in its preamble.

Some keys are **required** (no default). If omitted, the skill stops at its pre-flight and asks for the missing value. Required keys:

| Skill | Action | Required keys |
|---|---|---|
| `tf-refactor` | `rename`, `extract`, `for-each` | `from`, `to` |
| `tf-refactor` | `import` | `to` (the resource address being imported) |
| `tf-refactor` | `remove` | `from` (the address being removed from management) |
| `tf-cost` | `budget` | `threshold` |

## Parsing rules (for skill authors)

Skills parse `$ARGUMENTS` at the start of their body. The expected implementation:

1. Split on whitespace, respecting double-quoted regions.
2. For each token, split on the first `:` — left side is the key, right side is the value.
3. Unrecognised keys → warn and continue. Do not fail the skill.
4. Recognised keys with invalid values → stop at pre-flight with a clear error.

This is lenient on extra keys (forward-compatibility) and strict on values (type safety).

## Anti-patterns

- **Do not use `--flag` style.** The skills are not CLIs; `key:value` is the convention.
- **Do not use `=` as the separator.** Several existing Claude Code skills use `:` and mixing styles hurts discoverability.
- **Do not overload a single key** with multiple comma-separated values unless the skill explicitly documents it (e.g. `--only tf-test,tf-cost` in `install.sh`, not a skill argument).
- **Do not invent new shared keys** without updating this document. `target`, `env`, `action`, `format`, `from`, `to` are a contract.
