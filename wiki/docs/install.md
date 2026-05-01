# Installation & Setup

This guide will walk you through setting up Agentic-Z on your local machine. Follow these steps to prepare your environment for AI-powered DayZ modding.

## 1. Clone the Repository

Start by cloning this repository to your local machine.

```powershell
git clone https://github.com/DayZ-n-Chill/Agentic-Z.git MyNewMod
cd MyNewMod
```

## 2. Bootstrap the Environment

The template uses a sync system to make sure all your AI agents (Claude, Codex, Gemini) can see the specialized modding skills.

```powershell
python .claude/skills/sync-skills/sync.py
```

*Note: If you are using Claude Code, you can simply run `/sync-skills` from within the agent.*

## 3. Verify Prerequisites

DayZ modding requires specific tools from Bohemia Interactive. Run the preflight check to see what you're missing:

```powershell
python .claude/skills/dayz-preflight/preflight.py
```

### Required Native Tools
| Tool | Purpose |
|---|---|
| **DayZ Tools (Steam)** | Essential for packing PBOs and mounting the `P:\` drive. |
| **DayZ Diag** | Required for testing mods with `-filePatching`. |
| **Python 3.8+** | Required to run the automation scripts (skills). |

## 4. Mount the Work Drive (P:\)

DayZ Tools must have the `P:\` drive mounted for the engine and the packing tools to resolve file paths correctly.

You can mount it via the **DayZ Tools UI** or use our automation skill:
```powershell
python .claude/skills/dayz-mount-p/mount.py
```

## 5. Next Steps

Once your environment is verified and your drive is mounted, you are ready to start building.

- **[Scaffold your first mod](./dayz-modding#quick-start)** using the `/dayz-new-mod` skill.
- **[Meet your Agents](./agents/)** to start generating code and assets.
- **[Review the Conventions](./dayz-conventions)** to ensure your mod stays compatible with the template.
