# Cloud environment: developer skills

Use a dedicated Claude Code cloud environment to make the reviewed Matt Pocock
skills available to supervised cloud sessions and their subagents. Do not rely
on repository `enabledPlugins`: fresh cloud sessions have repeatedly shown that
project declarations do not trigger plugin installation.

## Recommended environment

Create a personal cloud environment named **Alpha Lab Dev**:

1. Open `claude.ai/code`.
2. Open the cloud-environment selector above the message box.
3. Choose **Add cloud environment**.
4. Set network access to **Trusted**.
5. Add this environment variable:

   ```text
   CLAUDE_CONFIG_DIR=/opt/alpha-lab-dev/claude-config
   ```

6. Paste the complete contents of
   `dev/cloud/setup-mattpocock-skills.sh` into **Setup script**.
7. Save the environment and start a new session in it.

`CLAUDE_CONFIG_DIR` is required. The setup script runs as root before Claude
Code launches, while the later Claude process may not share the setup shell's
`HOME`. Acceptance run 1 showed that environment variables configured in the UI
were not present in the pre-launch setup process. The script therefore exports
the fixed path internally for setup, while the configured environment variable
applies the same path to the later Claude process. Both lifecycle stages converge
on the same cache-stable plugin state.

The script is self-contained because cloud-environment setup-script ordering
does not guarantee that the repository is available before setup. It creates a
local marketplace under `/opt`, registers it at user scope, installs the plugin,
explicitly restores enablement on reruns, and writes a user-level `CLAUDE.md`
that points Alpha Lab sessions at `docs/agents/session-prompt.md`. It then fails
closed unless the enabled `claude plugin list` entry points at the installed
record carrying the expected SHA. The production paths are fixed beneath
`/opt/alpha-lab-dev`; arbitrary, relative, root, and symlinked paths are
rejected. The script does not broaden filesystem permissions. The first-session
acceptance therefore verifies that the later Claude process can read both the
root-created plugin state and user memory; incompatible setup/runtime identities
are rejected rather than made world-writable.

## What the setup installs

| Field | Value |
| :--- | :--- |
| Marketplace | `alpha-lab-pinned` |
| Plugin | `mattpocock-skills@alpha-lab-pinned` |
| Source | `https://github.com/mattpocock/skills.git` |
| Commit | `84fdeffd12f2ee307994d1eb6feb48173b6e0502` |
| Scope | user scope inside the selected cloud environment |
| User memory | `/opt/alpha-lab-dev/claude-config/CLAUDE.md` |

The explicit HTTPS source avoids SSH host-key and credential dependencies. The
plugin is pinned to the same upstream commit as
`dev/plugins/mattpocock-skills/`.

## Cache behavior

Claude's cloud-environment documentation states that the service snapshots
filesystem changes made by a successful setup script. Later sessions in the same
environment start from that snapshot and may skip setup. The acceptance process
below verifies that the documented behavior actually retains
`CLAUDE_CONFIG_DIR`, the local marketplace, and the installed plugin here.

Changing the environment setup script or allowed network hosts rebuilds the
cache. When updating the plugin:

1. review the upstream change;
2. update the SHA in the vendored provenance, setup script, and tests;
3. replace the setup-script text in the cloud environment;
4. start a new session and repeat acceptance.

## Acceptance before merge

Use a completely new session, not a resumed one:

1. Confirm `claude plugin list --json` reports
   `mattpocock-skills@alpha-lab-pinned` with `enabled: true`.
2. Confirm `~/.claude/plugins/installed_plugins.json`, or the equivalent path
   beneath `CLAUDE_CONFIG_DIR`, records the expected `gitCommitSha`.
3. Invoke `/mattpocock-skills:tdd`.
4. Launch a fresh subagent whose tools include `Skill` and have it independently
   discover and invoke the TDD skill.
5. Run `/memory` and confirm the user-level `CLAUDE.md` under
   `CLAUDE_CONFIG_DIR` loaded. Before manually pointing at `docs/agents/`, ask
   which issue tracker and domain docs the engineering skills should use; the
   answer must identify `docs/agents/issue-tracker.md` and
   `docs/agents/domain.md`, proving the startup pointer was followed.
6. Start a second new session in the same environment and repeat steps 1, 3,
   and 5 to prove the cached environment retains both plugin and pointer when
   setup is skipped.

Record distinct first-session and cached-session URLs, environment name, Claude
Code version, **Trusted** network mode, repository setup-script SHA-256, whether
the pasted setup text matches that reviewed script, whether setup ran or was
skipped, direct invocation, subagent invocation, fresh/cached configuration
pointer loading, and a UTC verification timestamp in the protected acceptance
receipt carried by the implementation PR.

Before starting the first session, calculate the canonical digest:

```bash
python -c 'import hashlib,pathlib; p=pathlib.Path("dev/cloud/setup-mattpocock-skills.sh"); print(hashlib.sha256(p.read_bytes().rstrip(b"\r\n")).hexdigest())'
```

Record that digest in the receipt and set `setupScriptDigestMatched` only after
confirming the environment setup field contains the same reviewed script. The
digest deliberately ignores trailing CR/LF characters because Claude's
environment editor trims the final newline when saving; all executable content
remains bound. Any later content change makes the PR check red again.

The PR-only workflow is a visible failing check, not a server-enforced merge
rule. ADR-0009 intentionally has no required PR gate; the human operator must
keep the PR draft and refuse merge until the receipt is verified.

## Scope boundary

The plugin is available to every session that uses this cloud environment,
regardless of repository. Prefer **Alpha Lab Dev** over the Default environment
unless that broader scope is intentional.

The GitHub Actions autonomous loop does not run in this cloud environment and
does not inherit its cached plugin state. If a future routine or autonomous
session is routed to Alpha Lab Dev, it will receive the plugin unless that
launch path disables `Skill` independently.

## Troubleshooting first-session authentication

`CLAUDE_CONFIG_DIR` redirects the entire Claude configuration, not only plugin
state. Anthropic-hosted cloud sessions normally receive authentication from the
session harness, but the first acceptance run must distinguish:

- **Unauthenticated session:** the shared config-directory handoff interfered
  with the cloud authentication path. Revisit the environment design before
  changing plugin logic.
- **Authenticated but skill missing:** setup, cache visibility, or plugin
  discovery failed. Inspect the setup output and plugin metadata.

Do not copy credentials into the repository or acceptance receipt.
