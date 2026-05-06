# Server-instance layout: task list

Branch: `feature/server-instance-layout`. Spec: `docs/superpowers/specs/2026-05-06-server-instance-layout-design.md`. Full plan with code: `docs/superpowers/plans/2026-05-06-server-instance-layout.md`.

| # | Task | Status |
|---|---|---|
| T1 | Create `dayz-add-server` skill (.claude/skills/dayz-add-server/{SKILL.md, add_server.py}). New skill, instance-based, replaces dayz-add-map. | done (commit 783b4e5) |
| T2 | Create `dayz-migrate-server` skill (.claude/skills/dayz-migrate-server/{SKILL.md, migrate.py}). One-shot legacy migration. | done (commit aa86cb5) |
| T3 | Refactor `dayz-launch-test`: --map → --server, .server/<instance>/ paths, old-layout gate, rewrite SKILL.md. | done (commit 311d797) |
| T4 | Update `dayz-clean-workspace`: target .server/ instead of workspace/_server/, refuse on legacy. | not started |
| T5 | Update `.claude-plugin/plugin.json`: register dayz-add-server + dayz-migrate-server, drop dayz-add-map. | not started |
| T6 | Rewrite server-runtime sections in `.claude/skills/_shared/dayz-conventions.md`. | not started |
| T7 | Update L1 docs (CLAUDE.md, AGENTS.md, GEMINI.md): replace workspace/_server/ paragraph with .server/ paragraph. | not started |
| T8 | Update `docs/dayz-modding.md`: skill name + path references throughout. | not started |
| T9 | Update README files + rename scripts/add-map.bat → scripts/add-server.bat. | not started |
| T10 | Add `.server/*/` to `.gitignore` with negation for serverDZ.cfg + mission/. | not started |
| T11 | Delete `.claude/skills/dayz-add-map/` folder. Final stale-reference grep sweep. | not started |
| T12 | Run `/sync-skills` and `/docs-sync` to propagate. | not started |
| T13 | End-to-end manual verification (real migration, fresh add, dry-run launch, dry-run clean, push, PR). | not started |

T1-T3 already shipped to the branch. T4-T13 not done yet. Nothing pushed.

Reply with which tasks (if any) to do next, or to discard the T1-T3 commits and start over.
