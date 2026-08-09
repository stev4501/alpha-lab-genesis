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

These are the defaults, kept unchanged. Four of the five do **not** exist on
`stev4501/alpha-lab-genesis` yet — `needs-triage`, `needs-info`,
`ready-for-agent`, `ready-for-human`. `wontfix` does exist (GitHub creates it
with every repository).

Nothing creates the missing four for you. `/triage` applies labels; neither this
configuration nor the triage skill defines a label-creation step, so applying a
label that does not exist will fail. Create them once before the first triage
run:

```bash
for l in needs-triage needs-info ready-for-agent ready-for-human; do
  gh label create "$l" --repo stev4501/alpha-lab-genesis || true
done
```

`ready-for-agent` means an AFK coding agent working from a GitHub issue. It does
**not** mean the autonomous research loop: that agent works from
`backlog/BL-XXXX-*.md`, never from GitHub issues, and cannot run these skills
(see `issue-tracker.md`). Labelling an issue `ready-for-agent` queues it for a
human-launched agent session, not for the loop.
