# AI pack

Reference for computer controlled characters: infected, animals, and patrols or guards built on them. Written in our own words from the vanilla files on `P:\`; every fact cites the file it came from. Used by `dayz-ai-specialist`; any DayZ worker may load one file when a task needs it.

| Question | Open |
|---|---|
| Which class do I extend, what runs each step, which hook do I override, what does the mind state mean? | `creatures.md` |
| How do I make infected see further, hear shots from further away, or scream louder? Where is `aiAgentTemplate` defined? | `behaviour-config.md` |
| How do I make a noise the AI reacts to, or react to gunfire in my own code? What makes a player visible? | `perception.md` |
| How do I make creatures walk a route or hold a post? Does vanilla have human AI? | `patrols-and-guards.md` |
| How do I spawn AI from script, what does the server lead need for the economy, and how do I keep it cheap? | `spawning-and-performance.md` |

Code from other mods is never copied into this pack or into a user's mod. Where a community approach is described, it is described in our own words only.
</content>
</invoke>
<invoke name="Bash">
<parameter name="command">cd /h/Projects/Agentic-Z/.claude/worktrees/wf_4ebf8f33-3c5-36/.claude/skills/_shared/ai && head -3 creatures.md