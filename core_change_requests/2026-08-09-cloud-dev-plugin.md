# CCR 2026-08-09: pinned cloud delivery for developer skills

- Origin: explicit operator request after PR #12 proved that
  `enabledPlugins` without a marketplace does not deliver skills to a clean
  cloud session.
- Status: **draft, blocked on fresh-cloud acceptance**.
- Protected paths: `.claude/`, `.github/`, `loop/`, and `scripts/`.
- Record patch:
  `core_change_requests/patches/2026-08-09-cloud-dev-plugin-protected-paths.diff`.
- Related: PR #17, issues #7 and #8, `docs/dev-only-skills.md`.

## Decision under review

Declare a repository-owned inline marketplace that resolves
`mattpocock-skills` from an HTTPS Git URL pinned to upstream commit
`84fdeffd12f2ee307994d1eb6feb48173b6e0502`. Enable that plugin for ordinary
project sessions.

The autonomous runner already passes `loop/agent-settings.json` through
`--settings`. Add the inverse `enabledPlugins: false` value for the same plugin
ID and retain the existing independent controls:

```text
--disable-slash-commands
--disallowedTools "Skill" "Read(dev/plugins/**)"
```

Pin the workflow CLI to the version used for compatibility probes and verify
the installed version before starting an autonomous session.

## Why this is not yet approved

Clean local probes prove that the inline marketplace resolves, the HTTPS source
installs the expected SHA when installation is explicitly requested, and the
runner settings override an installed plugin from enabled to disabled. They do
not prove that a fresh Claude Code cloud session automatically installs the
repository-declared plugin.

PR #17 therefore remains draft. Standard tests skip the pending cloud receipt
so autonomous validation remains operational. A separate pull-request workflow
fails until `.claude/cloud-plugin-acceptance.json` records:

1. a fresh Trusted-network cloud environment and session URL;
2. direct invocation of `/mattpocock-skills:tdd`;
3. installed metadata with the expected commit SHA; and
4. independent discovery and invocation by a subagent with the `Skill` tool.

## Governance

The operator explicitly requested this supervised PR. The protected-path diff
is retained as a review artifact and must be regenerated if any protected file
changes before merge. The receipt is under `.claude/`, so the autonomous agent
cannot approve its own release.

This change does not decide issue #7. Until that governance issue is resolved,
`dev/plugins/` and `bin/` remain agent-space.

## CORE_MANIFEST scope

`scripts/validate_cloud_plugin_acceptance.py` is deliberately not added to
`CORE_MANIFEST.json`. The manifest's sealed component is EV-0002's scientific
contract and evaluator chain; this script is pull-request gate tooling and does
not affect experiment semantics or cross-generation comparability.

The script is still human-owned and protected operationally: ADR-0009 assigns
`scripts/` to the human-owned core, `loop/agent-settings.json` denies edits to
that tree, and the protected-path patch retains the reviewed addition. Adding it
to the sealed component would require a generation bump for bookkeeping that
does not change the research system.

## Verification

```bash
python scripts/validate_repository.py
python -m unittest discover -s tests
python scripts/validate_cloud_plugin_acceptance.py  # intentionally red while pending
python -m py_compile bin/dev-session
bash -n loop/run_session.sh
git diff --check
```

## Rollback

Remove the inline marketplace and enabled plugin from
`.claude/settings.json`; remove the inverse plugin entry from
`loop/agent-settings.json`; restore the unpinned workflow install only after
recording the replacement compatibility policy; then remove the acceptance
workflow, validator, receipt, and related tests/documentation.
