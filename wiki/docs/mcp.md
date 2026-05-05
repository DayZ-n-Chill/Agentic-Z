---
sidebar_position: 5
sidebar_label: MCP Servers
title: MCP Servers
---

# MCP Servers

MCP (Model Context Protocol) servers extend an agent's tool kit. They run alongside Claude Code, Codex, or Gemini and expose new functions the agent can call: search a database, fetch a web page, query GitHub, read a custom corpus.

Agentic-Z ships with one MCP server bundled (`dayz-rag`). Two more are recommended optional adds.

## Bundled: `dayz-rag`

The local semantic-search server over the vanilla DayZ source plus the Bohemia community wiki. Powers the `search_dayz_source`, `search_dayz_wiki`, `get_dayz_file`, and `list_indexed_sources` tools available to every DayZ specialist agent.

| | |
|---|---|
| **Source** | `.claude/mcp/dayz-rag/` |
| **Setup** | Build the index once with **[`/dayz-search-index`](./skills/dayz-search-index)** or pull a prebuilt one with **[`/dayz-search-download`](./skills/dayz-search-download)** |
| **Tools added** | `search_dayz_source`, `search_dayz_wiki`, `get_dayz_file`, `list_indexed_sources` |
| **Backend** | Local vector DB (LanceDB) + Voyage embeddings (`voyage-code-3`) |

## Optional: GitHub MCP

[`@modelcontextprotocol/server-github`](https://github.com/modelcontextprotocol/servers/tree/main/src/github) lets agents read and write GitHub repos: list issues, comment on PRs, search code, fetch file contents, manage releases.

### When it helps

- Accepting community contributions on the Agentic-Z repo (or your own DayZ mod repo).
- Letting an agent triage issues, draft PR descriptions, or check CI status from inside the chat.
- Fetching a specific file from another GitHub repo without cloning.

### Setup

1. Create a [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` and `read:org` scopes.
2. Open `.claude/settings.json` (or `~/.claude/settings.json` for user-wide) and add the MCP server:

   ```json
   {
     "mcpServers": {
       "github": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-github"],
         "env": {
           "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
         }
       }
     }
   }
   ```

3. Restart Claude Code. Type `/mcp` to confirm `github` shows up as connected.
4. Tools like `mcp__github__list_issues`, `mcp__github__get_file_contents`, etc. are now callable.

## Optional: Web-fetch MCP

[`@modelcontextprotocol/server-fetch`](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) lets agents pull live web pages. Useful when the local DayZ RAG is stale, when an answer is on a forum, or when you want to read a community guide.

### When it helps

- Bohemia community wiki edits since the last RAG index build.
- Forum threads, blog posts, or Steam guides about DayZ modding patterns.
- Scraping a release page or change log.

### When to skip it

If you only ever ask about vanilla DayZ that's already in the RAG, this adds nothing. The local index is faster and offline.

### Setup

1. No API key needed.
2. Add to `.claude/settings.json`:

   ```json
   {
     "mcpServers": {
       "fetch": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-fetch"]
       }
     }
   }
   ```

3. Restart Claude Code. `/mcp` should list `fetch` as connected.
4. Agents can now call `mcp__fetch__fetch` with a URL to read a page.

## Adding your own MCP

Anything that speaks the Model Context Protocol can be added. The shape of an entry in `mcpServers` is:

```json
{
  "mcpServers": {
    "your-server-name": {
      "command": "<binary or interpreter>",
      "args": ["<args>"],
      "env": { "<KEY>": "<value>" }
    }
  }
}
```

For DayZ-specific MCPs you might write yourself (Steam Workshop API wrapper, custom asset indexer, etc.), drop them under `.claude/mcp/<name>/` and reference the binary path. The pattern matches how `dayz-rag` is bundled.

## After adding an MCP

- **Restart the agent CLI** so it picks up the new server. Hot-reload doesn't apply to MCP config.
- Run `/mcp` to confirm the server is connected. Disconnected servers don't surface their tools to the agent.
- Tool names are namespaced: `mcp__<server>__<tool>` so they don't collide with built-ins or other servers.
