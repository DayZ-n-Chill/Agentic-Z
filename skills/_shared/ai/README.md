# AI pack

Reference for computer controlled characters: infected, animals, and patrols or guards built on them. Facts about the vanilla game cite the vanilla file and line on `P:\`. Used by `dayz-ai-specialist`; any DayZ worker may load one file when a task needs it.

| Question | Open |
|---|---|
| Which class do I extend, what runs each step, which hook do I override, what does the mind state mean? | `creatures.md` |
| How do I make infected see further, hear shots from further away, or scream louder? Where is `aiAgentTemplate` defined? Why does a calm infected never vault (path filters)? | `behaviour-config.md` |
| How do I make a noise the AI reacts to, or react to gunfire in my own code? What makes a player visible? | `perception.md` |
| How do I make creatures walk a route or hold a post? Does vanilla have human AI, which class does a human NPC inherit, and can it run with no client? | `patrols-and-guards.md` |
| How do I spawn AI from script, what does the server lead need for the economy, and how do I keep it cheap? | `spawning-and-performance.md` |
| Where do animals live in the mission: `cfgenvironment.xml`, the `env\*_territories.xml` zone files, behaviour names and the group templates they select? | `animal-territories.md` |
| How is a creature tied to its animation graph and AI template, where are each creature's graph files, and which two bones does the engine move and aim? (Graph commands and variables are in the animation pack, linked from there.) | `creature-animation.md` |
| What does a custom infected inherit, how is its config laid out, what must its model keep for the AI, and what did 1.30 change for infected? | `custom-infected.md` |
| How do I design a scripted brain for a human guard or my own creature logic: a sleeping state, entering and leaving combat, seeing targets cheaply, costed paths, spreading a squad over targets? Why do my units flicker, freeze or all chase one player? | `design-ideas.md` |

What 1.30 changed for AI is spread over the files that own each topic: weather and noise in `perception.md`, `MINDSTATE_COWER` in `creatures.md`, `AIParams`, team friends and the Nasdara animal templates in `behaviour-config.md`, the Nasdara group templates and the navmesh format in `patrols-and-guards.md`, the Nasdara territories in `animal-territories.md`, the Nasdara animal graphs in `creature-animation.md`, and the new infected classes in `custom-infected.md`.

The mission economy and territory files cited here are the vanilla copies on `P:\` under `P:\DZ\worlds\<map>\ce\`. Line numbers match the vanilla data at the time of writing; when a line has moved, Grep the class or key name in the same file.

Code from other mods is never copied into this pack or into a user's mod. Where a community approach is described, it is described in our own words only.
