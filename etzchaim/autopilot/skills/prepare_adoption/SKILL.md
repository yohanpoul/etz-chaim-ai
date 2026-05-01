---
name: prepare-adoption
description: Drafts adoption assets (Discord welcome bot, HN launch post, Twitter thread, outreach pack). Does NOT launch; only prepares ready-to-review drafts. Operator triggers actual launch when paper is accepted.
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [adoption, marketing, outreach]
    related_skills: [paper-writer]
---

# Prepare Adoption

## Overview

Builds out the adoption pack so that, once the operator decides to launch,
all artifacts are ready. The skill never publishes ; it only stages drafts
under `~/.etz-chaim/autopilot/adoption/`.

## When to use

After `validate-edge` reports significant edge for 4 consecutive weeks
AND the paper draft is at "submission-ready" status.

## Outputs (drafts only)

- `~/.etz-chaim/autopilot/adoption/discord_setup.md`
  - Channel structure
  - Welcome bot script (neutral copy)
  - Office-hours bot config
- `~/.etz-chaim/autopilot/adoption/hn_post.md`
  - 250-word launch post
  - Discussion thread seeds
- `~/.etz-chaim/autopilot/adoption/twitter_thread.md`
  - 8-tweet thread
- `~/.etz-chaim/autopilot/adoption/outreach_pack/`
  - One template per academic lab targeted (Yarin Gal, Karpathy, Princeton SWE-agent, etc.)
  - Mail merge fields documented

## Steps

1. Read latest validate-edge report. If edge not validated, abort with
   status `edge_not_validated`.
2. Read paper draft state. If not submission-ready, abort.
3. Generate each adoption artifact ; run public surface guard on each.
4. Place artifacts under `~/.etz-chaim/autopilot/adoption/`.
5. Emit event `adoption_pack_ready`.
6. Do NOT push, post, send, or publish anything.

## Guardrails

- No external API calls (Discord API, Twitter API, mail send).
- No git commits ; outputs are outside the repo.
- All artifacts validated against `check_public_surface.sh` (no Hebrew).
- Operator approves each artifact individually before any launch.

## Verification checklist

- [ ] Each artifact written
- [ ] Each artifact passes the public surface guard
- [ ] No external API call performed
- [ ] No git commit / push performed
- [ ] `adoption_pack_ready` event emitted
