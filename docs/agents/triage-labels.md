# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those
roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the
corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Notes for this repo

These are the defaults, kept unchanged. **All five exist on
`stev4501/alpha-lab-genesis` as of 2026-08-09.** `wontfix` ships with every
repository; the other four were created during the first `/triage` run:

| Label             | Colour   |
| ----------------- | -------- |
| `needs-triage`    | `fbca04` |
| `needs-info`      | `d4c5f9` |
| `ready-for-agent` | `0e8a16` |
| `ready-for-human` | `1d76db` |

The two category roles `bug` and `enhancement` are GitHub defaults and also
already present, so the full triage vocabulary is in place. Nothing below needs
running unless a label is deleted.

### Recreating them

Nothing creates these for you. `/triage` applies labels; neither this
configuration nor the triage skill defines a label-creation step, so applying a
label that does not exist will fail. Both recipes are idempotent, so either is
safe to re-run.

**Local terminal**, where `gh` is available:

```bash
set -e
for l in needs-triage needs-info ready-for-agent ready-for-human; do
  gh label create "$l" --force --repo stev4501/alpha-lab-genesis
done
```

**Cloud and web sessions**, where `gh` is not installed. Label creation is one
of the operations the GitHub MCP server does not cover — it offers `get_label`
but no create-or-update tool — so this is the REST fallback that
`issue-tracker.md` authorises under "REST fallback in cloud sessions, narrowly
scoped". Read those conditions before using it; the same file's table is where
a newly discovered gap gets recorded. `GH_TOKEN` is present in the environment
and authenticates through the agent proxy.

```bash
set -e
API="https://api.github.com/repos/stev4501/alpha-lab-genesis/labels"
payload() {  # name colour description
  python3 -c 'import json,sys; print(json.dumps({"name":sys.argv[1],"color":sys.argv[2],"description":sys.argv[3]}))' "$1" "$2" "$3"
}
ensure_label() {  # name colour description -- creates, or updates if present
  code=$(curl -sS -o /tmp/label.json -w '%{http_code}' -X POST "$API" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -d "$(payload "$1" "$2" "$3")")
  # 422 means it already exists; PATCH it to the canonical colour/description.
  [ "$code" = "422" ] && code=$(curl -sS -o /tmp/label.json -w '%{http_code}' \
    -X PATCH "$API/$1" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -d "$(payload "$1" "$2" "$3")")
  case "$code" in 200|201) echo "ok $1" ;; *) echo "FAILED $1 -- HTTP $code"; return 1 ;; esac
}
ensure_label needs-triage    fbca04 'Maintainer needs to evaluate this issue'
ensure_label needs-info      d4c5f9 'Waiting on reporter for more information'
ensure_label ready-for-agent 0e8a16 'Fully specified, ready for an AFK agent'
ensure_label ready-for-human 1d76db 'Requires human implementation'
```

Confirm the result with `mcp__github__get_label` for each name afterwards, per
the read-back condition — the labels above were verified that way.

In both recipes, failures are deliberately **not** suppressed: an auth,
permission, network, or wrong-repo error must surface, because a silently
skipped label makes the first `/triage` run fail at the point of applying it.

`ready-for-agent` means an AFK coding agent working from a GitHub issue. It does
**not** mean the autonomous research loop: that agent works from
`backlog/BL-XXXX-*.md`, never from GitHub issues, and cannot run these skills
(see `issue-tracker.md`). Labelling an issue `ready-for-agent` queues it for a
human-launched agent session, not for the loop.
