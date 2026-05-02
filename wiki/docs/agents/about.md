---
sidebar_position: 0
sidebar_label: About Agents
title: About the Agents
---

# About the Agents

Agentic-Z ships with twelve specialist agents. Each one owns a slice of the DayZ stack and has its own model, color, and judgment style. You don't need to memorize the roster: ask a question, and the right specialist picks itself up.

:::warning[These are default starter agents]

Every agent here is a **starting point**. The baseline (vanilla source + wiki RAG, TrueDolphin's EnScript style guide, L1/L2 rules) covers most DayZ mods but **won't perfectly fit yours**. Expect to tune prompts, add agent memory, swap models, and write new specialists for what's missing.

:::

## What an agent is

A specialist AI persona with a focused domain. Every agent reads the L1 default rules and the L2 DayZ conventions before doing anything, so the rules stay aligned across all twelve. The agent's own definition adds the deep domain expertise on top.

## How they're grouped

- **Scripting & diagnosis** handle Enforce Script logic and crash forensics. They run on Opus for deep reasoning.
- **Content & assets** handle `config.cpp`, `.p3d` models, `.paa` textures, `.rvmat` materials, maps, and UI. They run on Sonnet because the work is pattern-driven.
- **Server & tooling** cover `types.xml`, `init.c`, server tuning, and Workbench plugin development. Sonnet handles the config-shaped work cleanly.
- **Meta agents** maintain the toolkit itself: pre-build mod review, wiki sync, scaffolding new agent definitions.

## Picking an agent

You usually don't. You ask a question in plain language and the right specialist takes it. The full roster sits below in this section. Click any agent for the detailed definition, default model, and example use cases.

If you want to change an agent's default model (Sonnet → Opus, Opus → Sonnet, etc.), see **[Model Selection](../model-routing)**.
