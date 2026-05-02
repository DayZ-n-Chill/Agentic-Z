---
sidebar_position: 0
sidebar_label: About Skills
title: About the Skills
---

# About the Skills

Skills are slash commands that automate the parts of DayZ modding you don't want to type by hand. Each one wraps a deterministic workflow: preflight, scaffold, build, launch, clean. The agents drive them under the hood; you can also call them directly when you know exactly what you want.

## What a skill is

A focused Python script with a `SKILL.md` definition. Skills don't make judgment calls. They run a workflow start-to-finish, surface useful output, and refuse loudly if the environment isn't in the right shape.

## The three phases

Skills group into three phases that map to how a DayZ session actually flows:

- **Setup** runs once per machine or once per mod. Verify the environment, mount `P:\`, scaffold a project, set up a test map. See the **[End-to-End Guide](../dayz-modding)** for the full setup table.
- **Iteration** is the loop you run repeatedly. Build the PBO, launch the test server with client, stop it when you're done.
- **Cleanup** wipes template-managed artifacts so the repo is ready to push or you can start fresh.

## How they connect to agents

Agents do the thinking. Skills do the doing. When you ask `dayz-script-specialist` to ship a change, the agent calls `/dayz-build-pbo` and `/dayz-launch-test` for you. The skills are the mechanical layer the agents drive. You don't have to memorize them, but you can call any of them directly when you want fine control.

The full skill list sits below in this section. Click any skill for its arguments, behavior, and the L2 conventions it enforces.
