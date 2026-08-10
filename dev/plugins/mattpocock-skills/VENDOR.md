# Vendored: mattpocock-skills

Third-party Claude Code plugin, vendored verbatim. Not authored here, not part
of the Alpha Lab core, and deliberately **not** discoverable by default.

## Provenance

| Field | Value |
| :--- | :--- |
| Upstream | https://github.com/mattpocock/skills |
| Commit | `84fdeffd12f2ee307994d1eb6feb48173b6e0502` |
| Upstream commit date | 2026-08-06 |
| Plugin version | 1.2.3 (`.claude-plugin/plugin.json`) |
| License | MIT (see `LICENSE`) |
| Vendored on | 2026-08-08 |

## What was copied

Exactly the 25 skill directories declared in the upstream `plugin.json`
`skills` array, plus `.claude-plugin/plugin.json` and `LICENSE`. The upstream
`deprecated/`, `in-progress/`, and `misc/` skill trees were **not** copied.

Files are byte-identical to upstream so that diffing against a newer upstream
tag stays clean. That includes the per-skill `agents/openai.yaml` files, which
are used by upstream's installer for non-Claude agents and are inert here.

## Why it lives under `dev/plugins/` and not `.claude/skills/`

`.claude/skills/` is a Claude Code auto-discovery path. Anything placed there
loads into **every** session in this repository — including the autonomous
research sessions launched by `loop/run_session.sh`. Those sessions operate
under a deliberately narrow mandate (`loop/prompts/session.md`), and several of
these skills (`implement`, `prototype`, `research`, `to-tickets`, `wizard`)
push an agent toward starting new self-directed work, which that mandate
forbids.

`dev/plugins/` is not a discovery path. The vendored copy is the reviewed source
and provenance reference. Supervised sessions receive the matching pinned plugin
through the dedicated **Alpha Lab Dev** cloud environment;
`loop/run_session.sh` does not use that environment and strips skills
independently.

See `docs/dev-only-skills.md` for the full rationale and the enforcement layers.

## Updating

```bash
git clone --depth 1 https://github.com/mattpocock/skills.git /tmp/mp-skills
# Diff, review, then re-copy the directories named in plugin.json.
# Record the new commit SHA, date, and version in the table above.
```

Review the diff before accepting it. These skills instruct an agent operating
in a repository whose integrity rules are enforced by convention as well as by
`loop/validate_session.sh`.

## Relationship to the marketplace copy

Anthropic's official marketplace ships this plugin pinned to the same commit
recorded above, so an install from there and this vendored tree agree today.
Nothing in this repository points at the marketplace: an attempt to declare it
via `enabledPlugins` was removed after a cloud-session probe showed the
declaration does not install anything. See `docs/dev-only-skills.md`.

If a future change does adopt the marketplace route, note that this repository
would not control the pin — the marketplace does, and it can change what runs
without any change here. Check for drift with:

    grep -A4 '"name": "mattpocock-skills"' \
      ~/.claude/plugins/marketplaces/claude-plugins-official/.claude-plugin/marketplace.json

The cloud-environment route in `dev/cloud/setup-mattpocock-skills.sh` does not
use the official marketplace. It creates an environment-local marketplace and
pins its HTTPS source directly to the commit recorded above. This is the sole
supported delivery route.

## Do not

- Do not copy or symlink these skills into `.claude/skills/`. That path loads
  into every session, and unlike the plugin route it is not what the runner's
  reasoning was verified against.
