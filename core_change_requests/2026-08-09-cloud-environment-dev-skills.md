# CCR 2026-08-09: install developer skills through a cloud environment

- Origin: explicit operator request after two fresh sessions disproved PR #17's
  repository-declaration approach.
- Status: **APPLIED** — landed on `main` 2026-08-09 via PR #27
  (`4b1551a`, "make Alpha Lab Dev the sole skills route"). All three files in
  the record patch are present on `main`, the acceptance receipt at
  `.claude/cloud-environment-plugin-acceptance.json` reads `verified`, and
  `scripts/validate_cloud_environment_acceptance.py` exits zero. The header
  said "ready for supervised merge review" until 2026-08-10; that was stale,
  not a pending review. The same PR also removed `bin/dev-session` — the
  cloud environment is now the only route to the developer skills, which is
  what "sole skills route" means and why `bin/` no longer exists.
- Protected paths: `.claude/`, `.github/`, and `scripts/`.
- Record patch:
  `core_change_requests/patches/2026-08-09-cloud-environment-dev-skills-protected-paths.diff`.
- Supersedes: PR #17's proposed repository `enabledPlugins` route.
- Related: issues #7 and #8; `docs/cloud-environment-dev-skills.md`.

## Decision under review

Use a dedicated **Alpha Lab Dev** Claude Code cloud environment. Configure:

```text
Network access: Trusted
CLAUDE_CONFIG_DIR=/opt/alpha-lab-dev/claude-config
Setup script: complete contents of dev/cloud/setup-mattpocock-skills.sh
```

The setup script runs before Claude launches. It creates a cache-stable local
marketplace, pins the plugin source to upstream commit
`84fdeffd12f2ee307994d1eb6feb48173b6e0502`, registers and installs it explicitly,
then fails unless installed metadata and `claude plugin list` confirm the
expected SHA and enabled state.

The fixed `CLAUDE_CONFIG_DIR` is the handoff between the root setup process and
the later Claude process. It also places plugin state in the environment's
filesystem cache so later sessions can use it when setup is skipped.

## Why repository settings are not used

PR #17 tested `extraKnownMarketplaces` plus `enabledPlugins` in two independent
fresh cloud sessions on Claude Code 2.1.226. Neither session created a
marketplace, installed a plugin, or recognized the skill. Repository declarations
do not trigger cloud installation in the tested environment.

## Acceptance

The PR-only workflow remains red until
`.claude/cloud-environment-plugin-acceptance.json` records:

1. successful direct invocation in the first fresh session;
2. successful independent invocation by a subagent with `Skill`;
3. installed metadata at the expected SHA;
4. successful direct invocation in a second new session using cached state; and
5. distinct cloud session URLs, environment name, Claude version, setup-run and
   setup-skipped observations, Trusted network mode, the reviewed setup-script
   digest and match attestation, and a UTC timestamp.

Standard tests skip the pending receipt so the autonomous loop's validator
remains operational.

The workflow is not a server-enforced required check. ADR-0009 deliberately
removes that class of PR gate. The protected receipt and failing check make the
state explicit, while the operator remains responsible for keeping the PR draft
and unmerged until acceptance succeeds.

### Acceptance evidence

Acceptance completed on 2026-08-09:

| Run | Session | Result |
| :--- | :--- | :--- |
| First fresh session | `https://claude.ai/code/session_01Ds14JPgjR8CZXMADdfPqzE` | setup ran; pinned plugin enabled; direct and independent subagent TDD invocation passed |
| Second new session | `https://claude.ai/code/session_01JSgKixanpWvb426EaYRg7M` | provisioning omitted setup; cached plugin remained enabled at the same SHA; direct TDD invocation passed |

The protected receipt is `verified`, the PR-only acceptance validator exits
zero, and the standard suite has no skip.

## Scope

The environment-installed plugin is available to every session routed to
**Alpha Lab Dev**, regardless of repository. The GitHub Actions autonomous loop
does not run in this cloud environment. Routines or other autonomous cloud
sessions must not target Alpha Lab Dev unless they independently disable Skill.

This change does not resolve issue #7. `dev/` remains agent-space until that
separate governance decision is taken.

## Verification

```bash
python scripts/validate_repository.py
python -m unittest discover -s tests
bash -n dev/cloud/setup-mattpocock-skills.sh
python scripts/validate_cloud_environment_acceptance.py  # red while pending
git diff --check
```

The setup script was also run twice against Claude Code 2.1.226 with an empty
`CLAUDE_CONFIG_DIR`; both runs installed and verified the exact SHA.
