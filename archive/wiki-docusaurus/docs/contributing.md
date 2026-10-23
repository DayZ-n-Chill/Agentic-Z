---
sidebar_position: 2
sidebar_label: Contributing
title: Contributing
---

# Contributing

Every agent and skill in Agentic-Z started as a real problem someone hit while shipping a mod. If you customize an agent to handle something better, or build a new one for a workflow this template missed, your fix can land back in the upstream so the next person who installs gets it for free.

## Where to start the conversation

[Discord](https://discord.gg/dayznchill) is the fastest path. Drop in for:

- Discussing a change you want to make before you write code
- Proposing a new agent or skill
- Getting walked through the repo as a fresh contributor
- Reporting a bug that's blocking your mod work

When your improvements are ready, open an issue or PR on [GitHub](https://github.com/DayZ-n-Chill/Agentic-Z).

## Contributor setup

To work on Agentic-Z itself (not just use it), use the **clone install path** — see [Install & Setup → Option B](./install#option-b--clone-the-template-for-contributors--power-users). That gives you the full repo with all the source, tests, and tooling.

Once cloned, the root [`CONTRIBUTING.md`](https://github.com/DayZ-n-Chill/Agentic-Z/blob/main/CONTRIBUTING.md) walks you through:

- Branch rules (always branch off `develop`, never `main`)
- The standard contribution flow
- What belongs in the repo vs your own mod project
- How to test a new skill end-to-end

## Understand before you change

Before touching anything, skim the [Architecture](./architecture) page so you know how the L1 / L2 / L3 layers fit together. Editing an L3 skill is local; touching L2 conventions or L1 rules ripples through every agent.

## What kinds of contributions are welcome

- **New skills** for workflows the template doesn't cover yet (config patterns, asset pipelines, server admin tasks).
- **Improvements to existing skills** — bug fixes, error messages, edge-case handling.
- **New specialist agents** for domains we haven't covered (animation, sounds, UI theming, modded gear systems).
- **Documentation fixes** — typos, clarifications, missing context.
- **L2 convention additions** when you discover a DayZ quirk that's bitten you and the workaround should be encoded once.
- **Bug reports** with reproduction steps, even if you can't fix them yourself.

The more modders contribute, the sharper the toolkit gets for everyone. Whether you're a seasoned Enforce Script dev, a server admin, a 3D artist, or learning DayZ modding for the first time, your work has a place here.
