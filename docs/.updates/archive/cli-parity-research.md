# CLI parity research: giving Codex CLI and Gemini CLI the Agentic-Z agents, hooks and RAG search

Researched 2026-10-22, read only. Repo facts come from `origin/develop` at `2902f83` (merge of PR #144). CLI facts come from the official docs, with links in each section.

## TL;DR

- **Codex and Gemini get skills and nothing else today.** `/sync-skills` links the 45 skill folders (plus `_shared`) into `~/.agents/skills` (Codex) and `~/.gemini/skills` (Gemini), and both CLIs read the shared rules file (`AGENTS.md` / `GEMINI.md`, same text as `CLAUDE.md`). Neither CLI gets the 30 agents, the 5 hooks, the dayz-rag MCP server or the permission rules.
- **The README overclaims.** It says "The same agents and skills work in Claude Code, Codex CLI, and Gemini CLI." Only the skills do.
- **Codex CLI (0.163.0) now supports all four missing pieces natively.** It has custom agents (TOML), Claude-style hooks with almost the same stdin and stdout JSON, MCP in `config.toml`, and `.rules` files for shell commands (experimental). Gaps: no per-agent tool allowlist, no `--agent` start flag, no MCP config per agent, and file edits arrive as one `apply_patch` tool instead of Edit and Write.
- **Gemini CLI (0.65.0) supports them too, but the product is being retired.** Since 2026-06-18 Gemini CLI serves only Code Assist Standard and Enterprise licenses and paid API keys; consumer users were moved to **Antigravity CLI** (`agy`). Its subagents use Markdown with frontmatter, nearly the Claude format, but **subagents cannot start other subagents**, and **project-level policy files are disabled**.
- **Proposed build:** one generator, inside the sync-skills skill, writes `.codex/` and `.gemini/` from `.claude/` (agents, hook config, MCP config, permission rules). A small shared adapter in `hooks/` lets the existing hook scripts read and answer each CLI's JSON. A drift test, like `docs-sync --check`, keeps the generated files in step with the Claude sources.
- **Owner decisions needed:** whether to target Gemini CLI or Antigravity CLI; whether generated files are committed or created at sync time; how to map the `haiku` and `sonnet` model pins; and whether read-only agents that lose enforcement are acceptable.

---

## 1. What Codex and Gemini get today

### 1.1 Skills: delivered (with caveats)

- `.claude/skills/sync-skills/sync.py` reads `agents.json` and links every folder under `.claude/skills/` that has a `SKILL.md`, plus `_shared`, into each CLI's home folder. It uses symlinks, with a fallback to junctions on Windows.
- Targets in `agents.json`:
  - `claude`: `~/.claude/skills`, or `$CLAUDE_CONFIG_DIR/skills`.
  - `codex`: `~/.agents/skills`. The skill text notes that `CODEX_HOME` does not move this folder.
  - `gemini`: `~/.gemini/skills`, or `$GEMINI_CLI_HOME/.gemini/skills`. Gemini also reads `~/.agents/skills`, so it sees each skill twice through two links to the same folder.
- `test_sync_skills.py` pins these paths and never touches real home folders.
- **Caveat 1: some skills speak to Claude.** 14 `SKILL.md` files mention Claude-only tools or paths: the Agent tool, `subagent_type`, `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PROJECT_DIR`, `~/.claude`, `.claude/settings`, `statusLine` or `mcp__` names. They are agentic-z-update, dayz-init, dayz-launch-objectbuilder, dayz-launch-workbench, dayz-new-mod, dayz-record-correction, dayz-scope-mod, dayz-search-download, dayz-search-index, dayz-statusline, dayz-upgrade-guard, dayz-workdrive, docs-sync and sync-skills. Most still run in Codex and Gemini because the work is done by Python scripts. `dayz-statusline` is Claude-only, and `dayz-route` tells the user to start `claude --agent agentic-z:dayz-orchestrator`.
- **Caveat 2: the index lives under a Claude folder.** Several scripts hard-code `~/.claude/...` paths, for example `INDEX_ROOT = Path.home() / ".claude" / "dayz-search-index"` in the RAG server. These are absolute paths, so they work from any CLI. The folder name is just Claude-flavoured.
- `mods/agentic-z-panel` is a Claude Code mod (a UI panel) with no equivalent in the other CLIs. It is out of scope.

### 1.2 Rules file: delivered

- `CLAUDE.md`, `AGENTS.md` and `GEMINI.md` are byte-identical, enforced by `scripts/dev/test_repo_integrity.py` line 389.
- Codex reads `AGENTS.md` and Gemini reads `GEMINI.md` by default.
- The text refers to the Agent tool, "Superpowers" workflows and `/dayz-route` follow-ups that assume Claude's subagent model.

### 1.3 Agents: not delivered

- There are 30 files in `.claude/agents/`. Nothing in the repo converts or links them for another CLI, and there is no `.codex/` or `.gemini/` folder.
- Frontmatter fields in use:

| Field | Used by | Notes |
|---|---|---|
| `name` | all 30 | Quoted string |
| `description` | all 30 | One JSON-escaped string with `\n\n<example>...</example>` blocks |
| `tools` | all 30 | Comma list of `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `Skill`, `Agent`, `Agent(name, ...)` and `WebFetch`, plus MCP names in two forms: `mcp__dayz-rag__*` and `mcp__plugin_agentic-z_dayz-rag__*` |
| `model` | 3 | `haiku` for dayz-router and dayz-build-engineer, `sonnet` for dayz-docs-writer |
| `maxTurns` | most | 50; `dayz-lead` has 100 |
| `memory: project` | about 17 | Claude agent memory, stored in `.claude/agent-memory/` |
| `color` | all | Claude UI only |

- **Structure that matters for porting:**
  - `dayz-orchestrator` is meant to be the **main session** (`claude --agent dayz-orchestrator`). It may start only five named agents: `Agent(dayz-mod-architect, dayz-lead, ...)`.
  - `dayz-lead` is a **subagent that starts subagents** (`tools: ... Agent`). So the team is three levels deep: orchestrator, then lead, then worker.
  - Read-only gate agents (`dayz-mod-reviewer`, `dayz-mod-debugger`, `dayz-router`, `dayz-build-checker`) rely on their `tools` list to stay read-only. Some do list `Write` and `Edit` for writing reports.
  - Figma agents name the Figma MCP tools in three plugin namespaces.

### 1.4 Hooks: not delivered

Defined twice, in `.claude/settings.json` (clone, `$CLAUDE_PROJECT_DIR`) and in `hooks/hooks.json` (plugin, `${CLAUDE_PLUGIN_ROOT}`). The plugin copy has only the first three hooks.

| Hook | Event and matcher | Reads from stdin | Answers with |
|---|---|---|---|
| `hooks/paste_router.py` | UserPromptSubmit | `prompt`, `cwd` | `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":...}}`; never blocks |
| `hooks/scope_guard.py` | PreToolUse `Edit\|Write\|MultiEdit` | `tool_input.file_path`, `cwd` | `hookSpecificOutput.permissionDecision: "deny"` plus reason, when the edit targets another mod while `/dayz-scope-mod` is active |
| `hooks/edit_check.py` | PostToolUse `Edit\|Write\|MultiEdit` | `tool_input.file_path` | `{"decision":"block","reason":...}` with syntax problems in `config.cpp` and `.layout` files |
| `agentic-z-update/update.py --check --quiet` | SessionStart (clone only) | nothing | One plain text line, or nothing |
| `docs-sync/sync.py --check --quiet` | Stop (clone only) | nothing | `{"systemMessage": ...}` when the wiki is out of date |

- **Environment.** All three Python hooks take the project folder from `CLAUDE_PROJECT_DIR`, then from stdin `cwd`, then from the working directory. `shadowed_by_project()` uses `CLAUDE_PROJECT_DIR` so the plugin copy stands down when the clone copy exists (tested in `hooks/test_plugin_copy.py`).
- **Tests.** `hooks/test_edit_check.py`, `test_scope_guard.py`, `test_paste_router.py` and `test_plugin_copy.py` cover only Claude-shaped JSON.

### 1.5 RAG search (dayz-rag MCP server): not delivered

- `.claude/mcp/dayz-rag/server.py` is a FastMCP server over stdio. It has three read-only tools: `search_dayz_source`, `get_dayz_file` and `list_indexed_sources`. It reads the LanceDB index at `~/.claude/dayz-search-index/`.
- **Where the API key comes from.** `voyage_common.py` loads `VOYAGE_API_KEY` from the environment first, then a `.env` in the working folder or above, then the repo root `.env`. **The key reaches the server even when a CLI strips environment variables**, as long as it is in a `.env` file. Optional variables: `VOYAGE_MODEL`, `DAYZ_RAG_MAX_DISTANCE`.
- **Registration:**
  - Clone: `.mcp.json` runs `python .claude/mcp/dayz-rag/server.py` (a relative path), turned on by `"enabledMcpjsonServers": ["dayz-rag"]` in `.claude/settings.json`.
  - Plugin: `.claude-plugin/plugin.json` uses `${CLAUDE_PLUGIN_ROOT}/.claude/mcp/dayz-rag/server.py`.

### 1.6 Permissions: not delivered

From `.claude/settings.json`:

- **Allow:**
  - Version checks.
  - `npm list *`, `npm install`, `npm ci`.
  - `python` and `node` on `.claude/skills/*`, `.claude/mcp/*` and `scripts/**`.
  - PowerShell dot-sourcing of `.claude/skills/*`.
  - `scripts/**/*.bat`.
  - The three dayz-rag tools in both namespaces.
- **Deny:** `format`, `diskpart`, `Format-Volume`, `Clear-Disk`, `python -c`, `python -m`, `node -e`, `node -p`, `npm install *`, `npm i *`, `npx *`.
- **Also set:** the Superpowers marketplace and plugin. These have no Codex or Gemini equivalent.

### 1.7 Anything already specific to Codex or Gemini

- `AGENTS.md` and `GEMINI.md`, kept identical to `CLAUDE.md` by test.
- The `codex` and `gemini` entries in `agents.json` and their tests.
- `update.py` keeps `GEMINI.md` in its template file list.
- Docs mention all three CLIs: README, `docs/README.md`, `wiki/docs/architecture.md`, `wiki/docs/mcp.md` and `docs/model-routing.md`. `wiki/docs/mcp.md` says MCP servers "run alongside Claude Code, Codex, or Gemini", but nothing registers dayz-rag for those two.
- There is no `.codex/`, `.gemini/`, `.agents/`, `config.toml`, `.rules` or `gemini-extension.json` anywhere in the tree.
- CI (`.github/workflows/tests.yml`) runs `pytest .claude scripts/dev hooks` and `docs-sync --check`. It runs no Codex or Gemini binary.

---

## 2. What each CLI supports (official docs)

Labels: **STABLE** means documented, on by default and not marked experimental. **EXPERIMENTAL** means the docs say so or it needs a flag. **UNCONFIRMED** means not found in the official docs.

### 2.1 Codex CLI

- **Version:** latest 0.163.0 (`rust-v0.163.0`), released 2026-10-15.
- **Doc locations:** `developers.openai.com/codex/*` now redirects (HTTP 308) to `learn.chatgpt.com/docs/*`. The `docs/` folder in the GitHub repo is mostly stubs that link to the site. Doc pages carry no dates.

**Custom agents: STABLE.** Sources: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [config reference](https://learn.chatgpt.com/docs/config-file/config-reference).

- **Format and location:** one **TOML** file per agent, in `.codex/agents/` (project, trusted projects only) or `~/.codex/agents/` (user). Alternatively, `[agents.<name>] config_file = "..."` in `config.toml`.
- **Required fields:** `name`, `description`, `developer_instructions` (the prompt body).
- **Optional fields:** `model`, `model_reasoning_effort`, `model_reasoning_summary`, `model_verbosity`, skill toggles, and feature switches such as `features.shell_tool = false`.
- **No per-tool allowlist.** An agent cannot override `sandbox_mode`, `approval_policy` or `mcp_servers`; it inherits them from the parent.
- **Invocation:** the main session delegates on its own or when asked in plain language ("have reviewer check this"). The internal tool is `spawn_agent`, which hooks also match as `Agent`. `/subagents` switches between running agent threads.
- **No `--agent` start flag** (UNCONFIRMED that any equivalent exists). A `codex agents` subcommand exists ("agent command center"); its purpose was not confirmed.
- **Nesting depth is not documented** (UNCONFIRMED).

**AGENTS.md: STABLE.** Codex reads it from `~/.codex` and from each folder from the git root down to the working folder. `project_doc_fallback_filenames` can add other names; the size cap is 32 KiB by default. Source: [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

- The repo's `AGENTS.md` is 10,745 bytes on develop, well under the cap.

**Skills: STABLE.** Source: [build skills](https://learn.chatgpt.com/docs/build-skills).

- **Scanned folders:** project `.agents/skills` (from the working folder up to the repo root), user `~/.agents/skills`, admin `/etc/codex/skills`, and the bundled skills.
- Symlinks are followed. `~/.codex/skills` is not a scanned folder.
- **Invocation:** `$skill-name` or `/skills`.
- **Custom prompts** (`~/.codex/prompts`) are deprecated in favour of skills.

**Hooks: STABLE (inferred).** On by default, turned off with `[features] hooks = false`. Source: [hooks](https://learn.chatgpt.com/docs/hooks).

- **Events:** `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `Interrupt`, `SessionStart`, `SessionEnd`. **All five Agentic-Z events exist under the same names.**
- **Config:**
  - Project: `.codex/hooks.json` or `[hooks]` in `.codex/config.toml`, loaded only when the project is trusted.
  - User: `~/.codex/hooks.json` or `config.toml`.
  - Plugin: `hooks/hooks.json`.
  - All layers run.
  - **Each hook must be approved in `/hooks` before it runs.** Approval is tied to a hash of the hook definition.
- **Format:** event, then matcher group (regex), then handlers. Handler fields: `type: "command"`, `command`, **`commandWindows`** (a Windows override), `timeout` (seconds, default 600), `statusMessage`, `additionalContextLimit` and `async`.
- **Stdin:**
  - Every event: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`.
  - Tool events: `tool_name`, `tool_input`, `tool_use_id`. PostToolUse adds `tool_response`.
  - UserPromptSubmit: `prompt`.
  - Stop: `stop_hook_active` and `last_assistant_message`.
- **Tool names hooks see:**
  - `Bash` for shell commands.
  - **`apply_patch` for every file edit.** It is also matched by `Edit` or `Write`, so the existing matcher `Edit|Write|MultiEdit` should fire.
  - `mcp__<server>__<tool>` for MCP tools.
  - `spawn_agent`, which also matches `Agent`.
- **Blocking:**
  - Exit 2 with the reason on stderr.
  - Or `hookSpecificOutput.permissionDecision: "deny"` with `permissionDecisionReason` (PreToolUse).
  - Or the legacy `{"decision":"block","reason":...}` (UserPromptSubmit, PostToolUse, Stop, SubagentStop). On PostToolUse it replaces the tool result with the reason.
- **Adding context:** `hookSpecificOutput.additionalContext` works on SessionStart, PreToolUse, PostToolUse and UserPromptSubmit. Plain stdout also becomes context on SessionStart and UserPromptSubmit.
- **`CLAUDE_PROJECT_DIR` is not set** (no alias was documented).
- **UNCONFIRMED: the exact `tool_input` shape for `apply_patch`.** It is very likely the patch text (`*** Update File: <path>` headers), not a `file_path` field. This needs a captured real payload before writing the adapter.

**MCP: STABLE.** Source: [MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

- **Config:** `[mcp_servers.<name>]` in `.codex/config.toml` (trusted projects) or `~/.codex/config.toml`.
- **Fields:** `command`, `args`, `cwd`, `env` (literal values), **`env_vars`** (names to forward from the parent environment), `startup_timeout_sec` (default 10), `tool_timeout_sec`, `enabled_tools` / `disabled_tools` (bare tool names), `default_tools_approval_mode` (`auto`, `prompt`, `writes` or `approve`), and per tool `tools.<tool>.approval_mode`.
- **Command line:** `codex mcp add <name> --env K=V -- <cmd>` writes to the user config.
- **Tool names:** hooks see `mcp__<server>__<tool>`. The name format the model sees is UNCONFIRMED.

**Permissions: STABLE for approvals and sandbox, EXPERIMENTAL for rules.** Sources: [config reference](https://learn.chatgpt.com/docs/config-file/config-reference), [rules](https://learn.chatgpt.com/docs/agent-configuration/rules), [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

- **Approval and sandbox settings:**
  - `approval_policy`: `on-request`, `never`, or a granular table.
  - `sandbox_mode`: `read-only`, `workspace-write` or `danger-full-access`.
  - `default_permissions` profiles.
  - Per-project `[projects."<path>"] trust_level = "trusted"`.
- **Rules (EXPERIMENTAL; "Rules are experimental and may change"):**
  - `rules/*.rules` beside each config layer, including `.codex/rules/` for trusted projects.
  - Syntax: `prefix_rule(pattern=[...tokens...], decision="allow"|"prompt"|"forbidden", justification=..., match=[...], not_match=[...])`.
  - Patterns are **exact token prefixes** with alternatives allowed. There is no glob inside a token.
  - `allow` runs the command **outside the sandbox** without asking.
  - Rules cover shell commands only. MCP tools are governed by `approval_mode`.
  - Test with `codex execpolicy check`.

**Plugins: STABLE format, partial.** Sources: [build plugins](https://developers.openai.com/plugins/build/plugins) and [plugins](https://learn.chatgpt.com/docs/plugins).

- **A plugin can bundle** skills, MCP servers (`mcp.json` / `.mcp.json`; the docs contradict each other on the name), hooks, apps and assets. **Custom agents are not a plugin component.**
- **Plugin hooks are documented only for manual installs in the desktop app** (CLI support is UNCONFIRMED).
- **Marketplace files:** `.agents/plugins/marketplace.json`, and **`.claude-plugin/marketplace.json` is read as a legacy-compatible format**. The plugin manifest format is not documented as Claude-compatible.
- **Commands:** `codex plugin marketplace add owner/repo`, `/plugins`.

### 2.2 Gemini CLI

- **Product status (from the [Google Developers Blog, 2026-05-19](https://developers.googleblog.com/en/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)):** from 2026-06-18 Gemini CLI stopped serving free, Google AI Pro and Ultra users. It still works for Code Assist Standard and Enterprise licenses and for paid Gemini or Agent Platform API keys.
- Every geminicli.com page carries the banner "Gemini CLI was replaced by Antigravity CLI on June 18th, 2026."
- Google says Antigravity keeps skills, hooks, subagents and extensions (as "plugins"), but without 1:1 parity at launch. Antigravity's file formats were not researched.
- **Versions:** latest stable 0.65.0 (Oct 20), preview 0.66.0-preview.0, nightly 0.67.0-nightly.20261022.
- **Doc pages are dated** from 2026-02-17 to 2026-10-06.

**Subagents: STABLE, on by default.** `experimental.enableAgents` defaults to `true`. Source: [subagents](https://geminicli.com/docs/core/subagents/), 2026-06-08.

- **Format and location:** Markdown with YAML frontmatter, where the body is the system prompt. Files go in `.gemini/agents/*.md` (project) or `~/.gemini/agents/*.md` (user).
- **Fields:**
  - `name`: a slug, which is also the agent's tool name.
  - `description`.
  - `kind`: `local` or `remote`.
  - `tools`: a list. If omitted, the agent gets every tool. Wildcards `*`, `mcp_*` and `mcp_<server>_*` work.
  - `mcpServers`: inline servers for this agent only.
  - `model`: default `inherit`.
  - `temperature`.
  - `max_turns`: default 30.
  - `timeout_mins`: default 10.
- **Invocation:** each agent is a **tool named after the agent**, so the model delegates on its own. Starting a prompt with `@name` forces it.
- **Subagents cannot call other subagents.**
- **No `--agent` start flag** (UNCONFIRMED; none is documented).

**Context file: STABLE.** `GEMINI.md` files are loaded from home, the workspace and its parents, and just in time. `context.fileName` can be an array, for example `["AGENTS.md","GEMINI.md"]`. Source: [GEMINI.md](https://geminicli.com/docs/cli/gemini-md/).

**Skills: STABLE.** Source: [skills](https://geminicli.com/docs/cli/skills/).

- **Folders:** `~/.gemini/skills` or `~/.agents/skills` (user), and `.gemini/skills` or `.agents/skills` (workspace). `.agents` wins within the same tier.
- **Activation:** the model calls `activate_skill`, then the user gives consent.

**Custom commands: STABLE.** TOML files in `.gemini/commands/` with `prompt` and `description`. Agentic-Z does not need them because skills cover the same ground.

**Hooks: STABLE, on by default.** `hooksConfig.enabled` defaults to `true`. Sources: [hooks](https://geminicli.com/docs/hooks/) and [reference](https://geminicli.com/docs/hooks/reference/), 2026-04-10.

- **Events, mapped to Claude's:**

| Gemini event | Claude equivalent |
|---|---|
| `BeforeTool` | PreToolUse |
| `AfterTool` | PostToolUse |
| `BeforeAgent` | UserPromptSubmit |
| `SessionStart` | SessionStart (adds context only, cannot block) |
| `AfterAgent` | Stop (can force a retry) |

  Gemini also has `SessionEnd`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `PreCompress` and `Notification`.
- **Config:** a `hooks` block in `settings.json` (project `.gemini/settings.json` takes precedence over user and system settings), or `hooks/hooks.json` in an extension.
  - Project hooks are fingerprinted, and the user is warned again whenever a hook's command changes.
  - Handler fields: `type: "command"` (the only type), `command`, `name`, `timeout` (**milliseconds**, default 60000).
  - Matchers are regular expressions on tool names.
- **Stdin:**
  - Every event: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`.
  - Tool events: `tool_name`, `tool_input`.
  - AfterAgent: `prompt_response`.
  - BeforeAgent: the prompt field name was not quoted (`prompt` is likely; UNCONFIRMED).
- **Environment:**
  - `GEMINI_PROJECT_DIR` is set, **and `CLAUDE_PROJECT_DIR` is set as a compatibility alias** (confirmed).
  - The environment is otherwise sanitized.
- **Tool names hooks see:** `write_file`, `replace` (edits), `read_file`, `read_many_files`, `glob`, `grep_search`, `list_directory`, `run_shell_command`, `web_fetch`, `google_web_search`, `activate_skill`, `write_todos`, `ask_user`. MCP tools appear as `mcp_<server>_<tool>`.
  - The `tool_input` field names for `write_file` and `replace` (expected `file_path`) were not quoted on the page I read (UNCONFIRMED; capture a real payload).
- **Answers:**
  - Exit 0 with JSON on stdout, or exit 2 with the reason on stderr (blocks). Invalid JSON on stdout is treated as allow and shown as a `systemMessage`.
  - JSON fields: `decision: "allow"|"deny"` (`"block"` is an alias), `reason`, `systemMessage`, `continue`, `stopReason`, `suppressOutput`, `hookSpecificOutput.additionalContext` (BeforeAgent and AfterTool) and `hookSpecificOutput.tool_input` (rewrites tool arguments in BeforeTool).
  - Whether Gemini also honours Claude's `hookSpecificOutput.permissionDecision` is UNCONFIRMED. Assume it does not.
- **`gemini hooks migrate`** (a Claude importer) appears only in a third-party cheat sheet (UNCONFIRMED; treat it as absent).

**MCP: STABLE.** Source: [MCP](https://geminicli.com/docs/tools/mcp-server/), 2026-10-06.

- **Config:** an `mcpServers` block in `.gemini/settings.json` or `~/.gemini/settings.json`.
- **Fields:** `command`, `args`, `cwd`, `env`, `timeout`, `trust` (skips confirmations), `includeTools` / `excludeTools`.
- **Variable expansion:** `$VAR` and `${VAR}` everywhere; `%VAR%` on Windows only.
- **The inherited environment is sanitized.** Any name matching `*KEY*`, `*TOKEN*`, `*SECRET*` and similar is stripped, **so `VOYAGE_API_KEY` is dropped unless listed in `env`**. In Agentic-Z the `.env` fallback still finds it.
- **Tool names:** `mcp_<server>_<tool>` with single underscores. Server names must not contain underscores, so `dayz-rag` is fine.
- **Command line:** `gemini mcp add -s project|user ...`.

**Permissions: mostly STABLE, but the project tier is missing.** Sources: [configuration](https://geminicli.com/docs/reference/configuration/) and [policy engine](https://geminicli.com/docs/reference/policy-engine/), 2026-04-30.

- **Settings:**
  - `tools.allowed` skips confirmation.
  - `tools.core` and `tools.exclude` exist; `exclude` is deprecated in favour of policy rules.
  - `--allowed-tools` is deprecated.
- **Approval modes:** `default`, `auto_edit`, `plan`, and `yolo` (command line only).
- **Policy engine:**
  - Rules are `.toml` files of `[[rule]]` blocks with `toolName`, `mcpName`, `commandPrefix`, `commandRegex`, `argsPattern`, `decision` (`allow`, `deny` or `ask_user`), `priority` and `denyMessage`.
  - **The workspace tier (`.gemini/policies/`) is "currently disabled"**, so a project cannot ship its own policy.
  - The user tier (`~/.gemini/policies/`) and admin tier work.
  - Extension policies work **except that `allow` is ignored there**.
- **Trusted folders** are on by default. Untrusted folders get read-only workspace settings (since 0.65.0).

**Extensions: STABLE.** Bundled agents are PREVIEW. Source: [extensions reference](https://geminicli.com/docs/extensions/reference/), 2026-05-14.

- **One extension can bundle:**
  - From `gemini-extension.json`: `mcpServers`, `contextFileName` / `GEMINI.md` and `settings` (environment variables, with sensitive values stored in the keychain).
  - From folders: `commands/*.toml`, `hooks/hooks.json`, `skills/<name>/SKILL.md`, `agents/*.md` (preview) and `policies/*.toml` (deny rules only).
- **Variables:** `${extensionPath}`, `${workspacePath}`, `${/}`.
- **Commands:** `gemini extensions install <git url|path>` and `gemini extensions link <path>`.
- There is no official Claude plugin importer.

---

## 3. Gap map

Key: **Native** means a direct equivalent exists. **Translate** means the same idea in a different format. **Partial** means it works with something lost. **None** means no equivalent.

### 3.1 By component

| Agentic-Z piece | Codex CLI | Gemini CLI |
|---|---|---|
| Skills (45, via `/sync-skills`) | **Done today** (`~/.agents/skills`). Could also go per project via a repo `.agents/skills` link. | **Done today** (`~/.gemini/skills` and `~/.agents/skills`). Each activation needs user consent. |
| Rules file | **Done** (`AGENTS.md`) | **Done** (`GEMINI.md`) |
| 30 agents: format | Translate: Markdown frontmatter becomes TOML, and the body becomes `developer_instructions` | Translate: nearly 1:1 Markdown frontmatter |
| Agents: `tools` allowlist | **None.** Only feature switches, for example `features.shell_tool=false` when the agent has no `Bash`. Read-only agents become read-only by instruction only. | Translate: map each tool name (table below). Enforced. |
| Agents: `model` (haiku, sonnet) | Translate to `model_reasoning_effort` (for example haiku becomes `low`) or a pinned model (decision needed) | Translate to a Gemini model or `inherit` (decision needed) |
| Agents: `maxTurns` | None | `max_turns` |
| Agents: `memory: project`, `color` | None; drop | None; drop |
| Orchestrator as main session (`claude --agent`) | **None.** Workaround: a skill such as `$dayz-orchestrate` that loads the orchestrator prompt into the main session. | **None.** Same skill workaround. |
| Orchestrator, then lead, then worker nesting | UNCONFIRMED (nesting depth not documented) | **None: subagents cannot start subagents.** The main session must do the lead's job, starting workers and gates directly. |
| `Agent(name, ...)` restriction | None | None (a deny policy on agent names exists only at user or admin tier) |
| Hook: paste_router (UserPromptSubmit) | Native event and field (`prompt`). The output format is already accepted. | Event `BeforeAgent`. Output needs `hookEventName: "BeforeAgent"` (UNCONFIRMED whether the name is checked). Prompt field likely `prompt`. |
| Hook: scope_guard (PreToolUse) | Native event and output. **Input must be translated:** edits arrive as `apply_patch` with a patch body, so file paths have to be parsed from the patch. A single patch can touch several files. | Event `BeforeTool`, matcher `write_file\|replace`. Input `tool_input.file_path` (UNCONFIRMED). **Output must be translated** to `{"decision":"deny","reason":...}`. |
| Hook: edit_check (PostToolUse) | Native event and output (`decision: block` replaces the tool result). Input from `apply_patch`, as for scope_guard. | Event `AfterTool`. `decision: block` (alias for deny) is accepted. Input `file_path`. |
| Hook: update check (SessionStart) | Native. Plain stdout becomes model context; Claude shows it to the user instead. Fine either way. | Native. Non-JSON stdout is shown as a `systemMessage`. Fine. |
| Hook: wiki drift (Stop) | Native, `systemMessage` | `AfterAgent`. `systemMessage` is a common output field. Fine. |
| Hook config | Translate to `.codex/hooks.json`, same nesting as Claude. Timeout in seconds. Use `commandWindows`. User must approve each hook in `/hooks`. | Translate to a `hooks` block in `.gemini/settings.json`. Event names change. Timeout in **ms**. Fingerprint warning on change. |
| `CLAUDE_PROJECT_DIR` in hooks | **Not set.** Scripts already fall back to stdin `cwd`. The command line must not depend on the variable. | Set (compatibility alias) |
| Plugin-copy shadowing (`shadowed_by_project`) | Not needed (no plugin hooks in the CLI) | Works if an extension and a clone are both active, because the alias is set |
| dayz-rag MCP | Translate to `[mcp_servers.dayz-rag]` in `.codex/config.toml`, with `env_vars=["VOYAGE_API_KEY","VOYAGE_MODEL","DAYZ_RAG_MAX_DISTANCE"]` and `default_tools_approval_mode="auto"` (all three tools are read-only) | Translate to `mcpServers.dayz-rag` in `.gemini/settings.json`, with `env: {"VOYAGE_API_KEY": "$VOYAGE_API_KEY", ...}` (otherwise stripped) and `trust: true` or a `tools.allowed` entry |
| MCP tool names in agent `tools` | Not applicable (no allowlist) | `mcp__dayz-rag__x` and `mcp__plugin_agentic-z_dayz-rag__x` become `mcp_dayz-rag_x` (remove duplicates) |
| Permissions: allow list | Partial: `.codex/rules/agentic-z.rules` (EXPERIMENTAL). There is no glob inside a token, so `python .claude/skills/*` cannot be written as one rule. The generator can list every `.py` script path instead. Note that `allow` runs outside the sandbox. | Partial: `tools.allowed` in project settings (deprecated route, but project-level). Policy `allow` rules work only in the user tier, which then applies to every project. |
| Permissions: deny list | Translate: `prefix_rule(["python","-c"], decision="forbidden")` and so on. PowerShell cmdlets inside `powershell -Command` strings will not match token prefixes. | Partial: extension `policies/*.toml` deny rules (work), or user-tier policy. **No project tier.** |
| Superpowers plugin | None | None |
| Plugin or extension packaging | Partial: a Codex plugin can carry skills, MCP and hooks (desktop app only) but **not agents**. The `.claude-plugin/marketplace.json` file is read. | Native: one extension can carry skills, MCP, hooks, agents (preview), deny policies and `GEMINI.md` |

### 3.2 Tool-name translation table (for agent `tools` and hook matchers)

| Claude | Codex (hook `tool_name`) | Gemini |
|---|---|---|
| Read | (built into the shell or reader; no hook name) | `read_file` (and `read_many_files`) |
| Write | `apply_patch` (matcher `Write` also works) | `write_file` |
| Edit, MultiEdit | `apply_patch` (matcher `Edit` also works) | `replace` |
| Glob | (no separate tool) | `glob` |
| Grep | (no separate tool) | `grep_search` |
| Bash, PowerShell | `Bash` | `run_shell_command` |
| WebFetch | hosted tool (hooks do not see it) | `web_fetch` |
| Skill | (skills via `$name`, no tool) | `activate_skill` |
| Agent | `spawn_agent` (matcher `Agent`) | each agent's own name; not allowed inside subagents |
| `mcp__dayz-rag__t` | `mcp__dayz-rag__t` | `mcp_dayz-rag_t` |

### 3.3 Agent text that needs light rewriting

- `dayz-lead`: "start each worker under `agentic-z:<name>`" and the Agent-tool workflow. Gemini cannot run this agent as a subagent at all.
- `dayz-orchestrator`: the `claude --agent ...` start instructions.
- `dayz-route` skill: "Tell the user to start `claude --agent agentic-z:dayz-orchestrator`."
- Descriptions are JSON-escaped strings with `<example>` blocks. They are valid for both CLIs once unescaped. Consider trimming the examples for Codex, since descriptions count against the delegation prompt.

**Recommended approach:** have the generator insert a short per-CLI preface into each body ("In Codex, delegate by name..." / "In Gemini you cannot start other agents; return your plan to the main session"), rather than forking the source files.

---

## 4. Proposed build

### 4.1 Principles

- `.claude/` stays the only source. Codex and Gemini files are **generated** and never edited by hand.
- Hook *scripts* are shared across all three CLIs. Only hook *config* is generated.
- Everything is testable offline with pytest. No Codex or Gemini binary is needed in CI.

### 4.2 Pieces

**1. Generator, at `.claude/skills/sync-skills/gen_clis.py`.** It goes in the existing skill folder so `/sync-skills` stays the single bootstrap; the repo rules say to extend existing tools before adding new ones.

- **Inputs:** `.claude/agents/*.md`, `.claude/settings.json` (hooks, permissions, `enabledMcpjsonServers`), `.mcp.json`, and a small mapping file `.claude/skills/sync-skills/cli_map.json`. The mapping file holds the tool-name table, event map, model map, timeout units and per-CLI body prefaces, so adding Antigravity later is mostly data.
- **Outputs in a clone:**
  - Codex:
    - `.codex/agents/<name>.toml`, 30 files: `name`, `description`, `developer_instructions`, mapped effort or model, and `features.shell_tool=false` when the source has no `Bash`.
    - `.codex/hooks.json`, with the five hooks, same events, `command` and `commandWindows`.
    - `.codex/config.toml`, with `[mcp_servers.dayz-rag]`.
    - `.codex/rules/agentic-z.rules`: deny rules plus allow rules for each skill and script entry point found on disk.
  - Gemini:
    - `.gemini/agents/<name>.md`, 30 files, with translated `tools`, `max_turns` and `model`. Skip, or mark main-session-only, any agent that needs `Agent`.
    - `.gemini/settings.json`, with `hooks` (renamed events, ms timeouts), `mcpServers.dayz-rag` and `tools.allowed`.
  - Possibly a repo-level `.agents/skills` link folder, so skills work per project without touching home folders. This is a decision: it overlaps the global links.
- **Outputs in user home** (optional, for use outside a clone, `--scope user`):
  - `~/.codex/agents/*.toml`, an MCP entry merged into `~/.codex/config.toml`, and `~/.codex/rules/agentic-z.rules`.
  - A generated Gemini extension folder `dist/gemini-extension/` (agents, skills links, hooks with `${extensionPath}`, MCP, deny policies, `GEMINI.md`), installed with `gemini extensions link`.
  - Merging into a user's own `config.toml` and `settings.json` must be additive and idempotent. Write only the `dayz-rag` table and the Agentic-Z hooks, and never rewrite other keys.

**2. Hook adapter, at `hooks/_cli.py`.** It is imported by the three Python hooks.

- **Detecting the CLI:**
  - Gemini: `hook_event_name` is `BeforeTool`, `AfterTool` or `BeforeAgent`.
  - Codex: `tool_name == "apply_patch"`, or a `model` or `turn_id` field is present without `CLAUDE_PROJECT_DIR`.
  - Otherwise Claude.
  - A `--cli` argument written by the generator is a simpler and more explicit alternative. Recommend the argument.
- **Normalizing input:** a list of edited file paths, parsed from `tool_input.file_path`, from `apply_patch` patch headers (`*** Add|Update|Delete File:`, `*** Move to:`), or from Gemini's `file_path`. Plus the prompt text and the project root.
- **Writing output in each CLI's format:**
  - Deny: Claude and Codex use `permissionDecision`; Gemini uses `decision: deny`.
  - Block after a tool: `decision: block` for all three.
  - Add context: `hookEventName` per CLI.
- `scope_guard` and `edit_check` loop over every path in a multi-file patch.

**3. Install.**

- `sync.py` calls the generator after linking, for each agent in `agents.json` that has a `generate` key. Add `"generate": "codex"` and `"generate": "gemini"` to `agents.json`.
- `--check` mode reports drift without writing, and CI runs it the same way as `docs-sync --check`.
- After install, print the one-time steps each CLI needs:
  - Codex: trust the project, approve hooks in `/hooks`, restart.
  - Gemini: trust the folder, accept the hook fingerprint prompt, `/skills reload`.

**4. Docs.** Fix the README claim. Add a parity table to `wiki/docs/` (docs-sync will need a source page). Update the `sync-skills` `SKILL.md`.

### 4.3 Offline tests (pytest, run in CI)

- **Generator, `test_gen_clis.py`:**
  - All 30 agents convert.
  - Every `tools` entry has a mapping: an unknown tool fails the test, so a new Claude tool cannot slip through silently.
  - Generated TOML parses with `tomllib`, and JSON and Markdown frontmatter parse with `json` / `yaml`.
  - Gemini names are valid slugs and MCP names become `mcp_dayz-rag_*`.
  - Agents that use `Agent` are handled per the decision for Gemini.
  - Golden-file tests for one worker, the orchestrator and the router.
  - Generated files equal the committed files (drift check).
  - Running twice is idempotent.
  - User-scope merging leaves unrelated keys untouched, tested on fixture files in `tmp_path` with the home folder redirected the way `test_sync_skills.py` does it.
- **Hooks:**
  - Extend `test_scope_guard.py`, `test_edit_check.py` and `test_paste_router.py` with Codex-shaped and Gemini-shaped stdin fixtures: an `apply_patch` body touching two mods, a `write_file` / `replace` input, a `BeforeAgent` prompt.
  - Assert each output is in the right CLI's format.
  - Test the case with no `CLAUDE_PROJECT_DIR`, using `cwd` only.
- **Config:**
  - Hook commands point at files that exist.
  - Timeouts are converted (seconds to ms for Gemini).
  - The MCP `args` path exists, and every env var the server reads is forwarded.
  - Every Claude deny rule has a counterpart in the Codex rules file, or appears in a documented "no equivalent" list.
- **Manual smoke test** (documented, not in CI): `codex exec` and `gemini -p` runs that trigger each hook and call `list_indexed_sources`.
  - **Step 0, before writing the adapter:** add a temporary logging hook in each CLI to capture real `apply_patch`, `write_file` / `replace` and `BeforeAgent` payloads, then commit them as test fixtures. This closes the UNCONFIRMED input shapes.

### 4.4 Suggested order

1. Capture the real hook payloads (step 0).
2. Write the hook adapter and its tests.
3. Generate the MCP config (smallest and highest value).
4. Generate the hook configs.
5. Generate the agents.
6. Generate the permission rules.
7. Write the docs.
8. Optional user-scope install and Gemini extension.

---

## 5. Decisions for the owner

1. **Gemini CLI or Antigravity CLI.** Gemini CLI now serves only enterprise and paid-API users, and Google points everyone else to Antigravity CLI. Options: target Gemini CLI as documented (it works today for paid keys), research Antigravity's formats first, or drop the Gemini target. Recommendation: build Codex first, and research Antigravity before spending on Gemini-specific output.
2. **Commit generated files, or create them at sync time.** Committing means a fresh clone works before `/sync-skills` and CI can check drift, at the cost of about 60 generated files in the tree. Recommendation: commit, with a drift test, matching the docs-sync pattern.
3. **Model mapping.** The `haiku` router and build engineer, and the `sonnet` docs writer. Recommendation: map by effort (Codex `model_reasoning_effort = "low"`; Gemini a flash-tier model or `inherit`), not pinned model IDs, which go stale.
4. **Read-only agents in Codex.** Codex cannot restrict an agent's edit tools, so reviewer, debugger and router are read-only only by instruction. Options: accept that, or have the PreToolUse hook deny `apply_patch` when `agent_type` (from SubagentStart) is a read-only agent. The second is UNCONFIRMED: it needs the agent identity in PreToolUse input.
5. **Team shape in Gemini.** With no nesting, `dayz-lead` cannot run as a subagent. Options: drop the lead layer in Gemini (the main session starts workers directly), or turn the lead into a skill the main session follows.
6. **Orchestrator start in both CLIs.** Neither has `--agent`. Recommendation: a `dayz-orchestrate` skill that loads the orchestrator prompt, and a change to `dayz-route` so it names the right start command for each CLI.
7. **Permission allows that bypass the sandbox.** Codex `allow` rules run commands outside its sandbox. Decide whether to generate allow rules at all, or only deny rules.
8. **Project-level versus global skills.** Adding a repo `.agents/skills` folder would make skills project-scoped in Codex and Gemini and avoid global links. It would also duplicate the global entries for anyone who already ran `/sync-skills`.

## 6. What could not be confirmed

- **Codex:**
  - The exact `apply_patch` `tool_input` shape.
  - Nesting depth for subagents.
  - Whether `codex agents` can start a session as an agent.
  - The MCP tool-name format the model sees.
  - Plugin hooks in the CLI.
  - Whether `.codex/config.toml` resolves a relative MCP `args` path from the project root (set `cwd` explicitly to be safe).
- **Gemini:**
  - The BeforeAgent prompt field name.
  - The `write_file` / `replace` input field names.
  - Whether Claude-style `permissionDecision` output is honoured.
  - How the `$GEMINI_PROJECT_DIR` hook command expands under the Windows shell.
  - `gemini hooks migrate`.
  - Antigravity CLI's formats.
- **Doc caveats:** Codex doc pages carry no dates; the Codex version and date come from the GitHub release. Codex pages were read through a summarizing fetcher, so a few snippets are rebuilt from documented field names.
