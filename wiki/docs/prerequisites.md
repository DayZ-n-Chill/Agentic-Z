# Prerequisites

Before you install Agentic-Z, your machine needs a handful of one-time setup pieces. Most are free, all of them are standard for DayZ modding regardless of whether you use this template.

You need a Windows machine with:

| Requirement | How to get it | Why |
|---|---|---|
| **DayZ** (the game) | [Steam](https://store.steampowered.com/app/221100/DayZ/) or [Bohemia Store](https://www.bohemia.net/games/dayz) | The client (`DayZ_x64.exe`) you'll use to test mods. |
| **DayZ Tools** | Steam → Library → Tools (free) | AddonBuilder, Binarize, P-drive mounting. |
| **DayZ Diag** | Comes with DayZ. `DayZDiag_x64.exe` lives next to `DayZ_x64.exe` in your DayZ install dir | The diagnostic build that allows `-filePatching` to function. Used for **both** client and server in `/dayz-launch-test`. Retail binaries block past the loading screen with filePatching on. |
| **`P:\` drive mounted** | Open DayZ Tools → mount the P drive, **OR** run `python .claude\skills\dayz-workdrive\mount.py` (auto-resolves the work drive from DayZ Tools' `settings.ini`) | DayZ Tools and the engine both read from `P:\`. Preflight hard-fails without it. `P:\` does not auto-mount; mount it at the start of each session. |
| **`P:\Mods\` junction** | One-time: `cmd /c mklink /J P:\Mods "<DayZ install>\!Workshop"` | The DayZ engine and Launcher load mods from `<DayZ install>\!Workshop\`. The `P:\Mods\` junction lets builds deploy via `P:\Mods\@<ModName>\Addons\<ModName>.pbo` and actually land where the engine reads. Build-pbo hard-fails if this junction is missing or points at a regular folder. |
| **Vanilla DayZ data on `P:\`** | DayZ Tools → "Extract Game Data" | Configs in your mod inherit from base classes (`ItemBase`, `Inventory_Base`, etc.) which only exist if vanilla PBOs are unpacked. |
| **Python 3.8+** on `PATH` | [python.org](https://www.python.org/downloads/) | The skills are Python scripts. |
| **Voyage AI API key** *(optional, only for RAG)* | Sign up at [voyageai.com](https://www.voyageai.com/), grab a key from [dashboard.voyageai.com](https://dashboard.voyageai.com/), add `VOYAGE_API_KEY=pa-…` to `.env` at the repo root | Powers `/dayz-rag-index` and the `dayz-rag` MCP server. Enables semantic search ("how does vanilla handle X?") over the indexed source. Embeddings via `voyage-code-3` (code-tuned, 1024-dim). Without it, agents fall back to `Grep` on the documented vanilla paths. Fully functional, just less smart. **Shortcut:** `/dayz-rag-download` pulls a prebuilt index from GitHub releases (~1 min). No key needed for download, but query-time still requires the key. |

## Why so much setup?

DayZ's engine and Tools have specific path expectations baked in: addons resolve through the `P:\` work drive, the Launcher loads mods from `<DayZ install>\!Workshop\`, and configs inherit from vanilla base classes. None of this is Agentic-Z's invention. It's how Bohemia ships the engine. The template's slash commands automate around these conventions so you don't have to think about them, but the underlying tools still need to exist.

## Once everything is in place

Head to **[Installation & Setup](./install)** to clone the repo and bootstrap the agent CLIs. That walkthrough assumes the prerequisites above are already done.
