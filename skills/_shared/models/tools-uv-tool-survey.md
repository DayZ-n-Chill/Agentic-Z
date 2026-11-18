# Automatic UV tools

Which automatic or AI unwrap tools could build a livery template atlas for a hard surface vehicle mesh, run locally on one GPU and be scripted, and why each was chosen, kept in reserve or dropped. The pipeline that won is in `tools-uv-atlas.md`. Nothing here is a game fact; prices and availability change.

| Tool | Verdict |
|---|---|
| Blender 4.3+ SLIM (`MINIMUM_STRETCH`) with your own seams | The backbone. The solver is production grade; the seams have to be supplied, and the region growing of `uv_view_charts.py` supplies them. Free and fully scriptable through bpy |
| PartUV (SIGGRAPH Asia 2025) | The only UV AI with code and weights. Tested and beaten 3 to 4 times over on island count (`tools-uv-partuv.md`). Kept as a chart source to experiment with |
| RizomUV VS (EUR 149.90, perpetual) | The best paid fallback: truly headless (`-cfi` Lua scripts and the RizomUVLink Python module). The livery look needs Size-Limiter tuning. Try the 15 day trial before buying, because script mode has had a regression bug |
| Ministry of Flat | Dropped: it improves packing through more islands, the opposite of this goal. Free for commercial use and has a CLI |
| xatlas, UVAtlas | Chart growers for lightmaps, confetti by design. TRELLIS.2 and Hunyuan3D call xatlas internally. UVAtlas is in maintenance mode |
| BFF, OptCuts, the SLIM paper | Solvers and cutters that minimize distortion or seam length; none groups by meaning. BFF flattens well once seams exist (organic focus) |
| Houdini Labs AutoUV | Its cluster method can cap the island count, but the Apprentice license cannot export usefully. Worth it only with a paid Houdini |
| Nuvo, Flatten Anything, AUV-Net, SeamGPT, ArtUV, SeamGen | Papers without usable code and weights. SeamGen and SATO are worth watching |
| PartField, P3-SAM (Hunyuan3D-Part) | AI mesh segmentation usable as a seam source (P3-SAM handles vehicles). The route: segment labels, then boundary edges, then Mark Seam, then SLIM |
| Cloud services (Tripo, Meshy, Rodin, fal.ai) | No cloud endpoint makes readable islands; the usual result is confetti. fal.ai has retopology (`hunyuan-3d/v3.1/smart-topology`, about USD 0.75 per generation) but no unwrap endpoint. TRELLIS.2 retexture and Hunyuan3D-Paint both call bare xatlas, so the TRELLIS.2 pipeline ignores a hand made UV |
| Quad Remesher (paid) | Retopology only, no UVs. Its edge flow helps seams. Retopology of a mesh meant to be seen needs the user's approval first |

There is no mature AI UV unwrapper product. The working answer is a classic solver plus good seams, where the seams come either from geometry analysis (the view chart pipeline) or from an AI segmenter feeding the same solver.
