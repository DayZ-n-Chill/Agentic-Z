# Automatic UV tool survey

Which automatic or AI unwrap tools were considered for this skill and why each was chosen, shortlisted or discarded. Researched on 2026-07-16; prices and availability are as of that date.

The question: what is the best automatic or AI tool for livery-template UV atlases on hard-surface vehicle meshes, running locally (an RTX 3090) and scriptable?

| Tool | Verdict for this quality gate |
|---|---|
| **Blender 4.3+ SLIM (`MINIMUM_STRETCH`) with your own seams** | The winner, as the backbone. The solver is production grade; the "intelligence" (the seams) has to be supplied, and this skill's region growing supplies it. Free and fully scriptable through bpy. |
| **PartUV** (SIGGRAPH Asia 2025) | The only real UV AI with code and weights. Piloted and beaten 3 to 4 times over on island count here; see `partuv-pilot.md`. Kept as a chart-source experiment. |
| **RizomUV VS** (EUR 149.90 perpetual) | The best commercial fallback: truly headless (`-cfi` Lua scripts and the RizomUVLink Python module). The livery look needs Size-Limiter tuning. Test the 15-day trial before buying, because script mode has had a regression bug. |
| Ministry of Flat | Discarded on philosophy: it optimizes packing through *more* islands, the opposite of this gate. Free for commercial use, has a CLI, but the wrong objective. |
| xatlas, UVAtlas | Chart growers for lightmaps; confetti by design. This is what TRELLIS.2 and Hunyuan3D call internally. UVAtlas is in maintenance mode. |
| BFF, OptCuts, the SLIM paper | Solvers and cutters that minimize distortion or seam length; none is semantic. BFF is a great flattener once seams exist (organic focus). |
| Houdini Labs AutoUV | Its cluster method can cap the island count, but the Apprentice license cannot export usefully. Only worth it if you already pay for Houdini. |
| Nuvo, Flatten Anything, AUV-Net, SeamGPT, ArtUV, SeamGen | Papers without usable code and weights as of 2026-07. Watch SeamGen and SATO. |
| PartField, P3-SAM (Hunyuan3D-Part) | AI mesh segmentation usable as a seam source (P3-SAM shows vehicles). The do-it-yourself route: segment labels, then boundary edges, then Mark Seam, then SLIM. |
| Cloud services (Tripo, Meshy, Rodin, fal.ai) | No cloud endpoint produces legible-island UVs; the usual result is exploded confetti. fal.ai has retopology (`hunyuan-3d/v3.1/smart-topology`, about USD 0.75 per generation) but no unwrap endpoint. TRELLIS.2 retexture and Hunyuan3D-Paint both call bare xatlas, so a hand-made UV is **ignored** by the TRELLIS.2 pipeline. |
| Quad Remesher (paid) | Retopology only, no UVs. Its edge flow helps seams. Retopology of a mesh meant to be seen needs the user's approval first. |

Bottom line: in 2026 there is still no mature "AI UV unwrapper" product. The production answer is a classic solver plus smart seams, where "smart" is either deterministic geometry analysis (this skill) or an AI segmenter feeding the same solver.
