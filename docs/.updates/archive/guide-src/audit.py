import re,sys
A_OLD='agent-creator dayz-asset-specialist dayz-build-checker dayz-build-engineer dayz-config-specialist dayz-docs-writer dayz-ingame-tester dayz-layout-validator dayz-lead dayz-map-specialist dayz-mod-architect dayz-mod-debugger dayz-mod-reviewer dayz-object-builder dayz-orchestrator dayz-script-specialist dayz-server-admin dayz-ui-specialist dayz-workbench-specialist figma-node-normalizer figma-to-dayz-layout'.split()
A_NEW='dayz-router dayz-persistence-specialist dayz-vehicle-specialist dayz-weapon-specialist dayz-wearables-specialist dayz-animation-specialist dayz-audio-fx-specialist dayz-physics-specialist dayz-ai-specialist'.split()
S_OLD='dayz-add-scaffold dayz-add-server dayz-build-imageset dayz-build-pbo dayz-clean-workspace dayz-cot-bootstrap dayz-deploy-pbo dayz-edit-types dayz-import-mod dayz-init dayz-launch-objectbuilder dayz-launch-test dayz-launch-workbench dayz-new-mod dayz-p3d-audit dayz-pack-texture dayz-particles dayz-preflight dayz-record-correction dayz-scope-mod dayz-search-download dayz-search-index dayz-search-wiki-index dayz-setup-objectbuilder dayz-split-types dayz-stop-test dayz-workdrive'.split()
S_NEW='dayz-gate dayz-route dayz-statusline dayz-panel dayz-lint dayz-conflict-check dayz-ask dayz-balance dayz-health dayz-logwatch dayz-recipe dayz-release-pack dayz-server-kit dayz-upgrade-guard'.split()
def sec(t,sid):
    s=t.index('<section aria-labelledby="%s">'%sid); return t[s:t.index('</section>',s)]
for fn,checks in (('agentic-z-guide.html',[('g-agents','A'),('h-grades','AS'),('h-grade-detail','AS'),('h-skills','S')]),('agentic-z-team.html',[('h-agents','A'),('h-grades','AS'),('h-grade-detail','AS'),('h-skills','S'),('h-chart','A')])):
    t=open(fn,encoding='utf-8').read()
    for sid,k in checks:
        x=sec(t,sid); full=(A_OLD+A_NEW if 'A' in k else [])+(S_OLD+S_NEW if 'S' in k else [])
        miss=[n for n in full if not re.search(r'(?<![\w-])/?%s(?![\w-])'%re.escape(n),x)]
        print(fn[11:15],sid,'missing',len(miss),miss)
