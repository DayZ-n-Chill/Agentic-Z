import pathlib, re
p = pathlib.Path(__file__).parent / 'agentic-z-team.html'
t = p.read_text(encoding='utf-8')
t = t.replace('<td>232 tests, a CI workflow,', '<td>1,064 tests, a CI workflow,')
t = t.replace('<td>232 tests pass:', '<td>1,064 tests pass. They check')
t = t.replace('<td>12 tests cover filters', '<td>54 tests cover filters')
before = {
'agent-creator':'A-','dayz-asset-specialist':'C+','dayz-build-checker':'A','dayz-build-engineer':'A-','dayz-config-specialist':'C+','dayz-docs-writer':'A-','dayz-ingame-tester':'A','dayz-layout-validator':'B-','dayz-lead':'A-','dayz-map-specialist':'C+','dayz-mod-architect':'A-','dayz-mod-debugger':'B-','dayz-mod-reviewer':'B','dayz-object-builder':'B-','dayz-orchestrator':'A-','dayz-script-specialist':'B-','dayz-server-admin':'C+','dayz-ui-specialist':'C','dayz-workbench-specialist':'C+','figma-node-normalizer':'B-','figma-to-dayz-layout':'C+',
'agentic-z-update':'B+','clean-repo':'B','dayz-add-scaffold':'B+','dayz-add-server':'B+','dayz-build-imageset':'B','dayz-build-pbo':'B','dayz-clean-workspace':'B-','dayz-cot-bootstrap':'B','dayz-deploy-pbo':'A-','dayz-edit-types':'C+','dayz-import-mod':'B+','dayz-init':'C','dayz-launch-objectbuilder':'A-','dayz-launch-test':'B+','dayz-launch-workbench':'B+','dayz-new-mod':'B',
'dayz-p3d-audit':'B','dayz-pack-texture':'B+','dayz-particles':'B+','dayz-preflight':'B','dayz-record-correction':'A-','dayz-scope-mod':'B','dayz-search-download':'B-','dayz-search-index':'C+','dayz-search-wiki-index':'C+','dayz-setup-objectbuilder':'B-','dayz-split-types':'B','dayz-stop-test':'A-','dayz-workdrive':'B+','docs-sync':'B','sync-skills':'B+',
'dayz-rag search server':'B+','DayZ rules file (Tier 2)':'n/a','Shared skill helpers':'n/a'}
latest = {
'agent-creator':'A+','dayz-asset-specialist':'A','dayz-build-checker':'A','dayz-build-engineer':'A-','dayz-config-specialist':'A+','dayz-docs-writer':'A','dayz-ingame-tester':'A','dayz-layout-validator':'A-','dayz-lead':'A+','dayz-map-specialist':'A+','dayz-mod-architect':'A+','dayz-mod-debugger':'A+','dayz-mod-reviewer':'A-','dayz-object-builder':'A-','dayz-orchestrator':'A','dayz-script-specialist':'A+','dayz-server-admin':'A+','dayz-ui-specialist':'A+','dayz-workbench-specialist':'A+','figma-node-normalizer':'A','figma-to-dayz-layout':'A+',
'agentic-z-update':'B+','clean-repo':'A+','dayz-add-scaffold':'A-','dayz-add-server':'B+','dayz-build-imageset':'A-','dayz-build-pbo':'B','dayz-clean-workspace':'A','dayz-cot-bootstrap':'A-','dayz-deploy-pbo':'A','dayz-edit-types':'A-','dayz-import-mod':'A-','dayz-init':'A-','dayz-launch-objectbuilder':'A','dayz-launch-test':'B+','dayz-launch-workbench':'A+','dayz-new-mod':'A',
'dayz-p3d-audit':'A-','dayz-pack-texture':'B+','dayz-particles':'A+','dayz-preflight':'A+','dayz-record-correction':'A-','dayz-scope-mod':'A+','dayz-search-download':'A','dayz-search-index':'A-','dayz-search-wiki-index':'D','dayz-setup-objectbuilder':'A','dayz-split-types':'A+','dayz-stop-test':'A+','dayz-workdrive':'A+','docs-sync':'A-','sync-skills':'A+',
'dayz-rag search server':'A+','DayZ rules file (Tier 2)':'B','Shared skill helpers':'A+'}

def cls(g):
    if g == 'A+': return 'ok'
    if g.startswith('A'): return 'keep'
    if g == 'n/a': return 'todo'
    if g.startswith('B'): return 'warn'
    return 'fix'

def now(name, g):
    if name == 'dayz-search-wiki-index': return '<span class="pill fix">On hold</span>'
    if g == 'A+': return '<span class="pill ok">A+</span>'
    return '<span class="pill move">Fixed, recheck</span>'

names = list(before)
groups = [('Agents', names[:21]), ('Skills', names[21:52]), ('Shared', names[52:])]
rows = []
for gname, group in groups:
    rows.append('<tr class="grp"><th colspan="4" scope="colgroup">%s</th></tr>' % gname)
    for n in group:
        b, l = before[n], latest[n]
        rows.append('<tr><th scope="row"><code>%s</code></th><td><span class="pill %s">%s</span></td><td><span class="pill %s">%s</span></td><td>%s</td></tr>' % (n, cls(b), b, cls(l), l, now(n, l)))
n_ap = sum(1 for v in latest.values() if v == 'A+')
section = '''<section aria-labelledby="h-grades">
 <h2 id="h-grades">Quality grades</h2>
 <p>Every agent and skill was graded against Anthropic's Claude Code best practices for agents and skills, then fixed and regraded five times. Each grade came from a separate reviewer that had not seen earlier grades. The first column is the first grade; the second is the most recent independent grade (%d of %d at A+). Everything below A+ in that column was fixed again afterwards, and those fixes still need one more independent check.</p>
 <div class="status-key"><span><span class="pill ok">A+</span> confirmed by the latest check</span><span><span class="pill move">Fixed, recheck</span> fixed after that check</span><span><span class="pill fix">On hold</span> waits on Brian's decision</span></div>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">First grade</th><th scope="col">Latest check</th><th scope="col">Now</th></tr></thead>
  <tbody>
   %s
  </tbody>
 </table></div>
 <p class="example">Tests went from 84 to 1,064 across the five rounds. The wiki indexer is on hold because it gets past the Bohemia wiki's Cloudflare check with a copied browser cookie.</p>
</section>

''' % (n_ap, len(latest), '\n   '.join(rows))
assert t.count('<section aria-labelledby="h-fix">') == 1
t = t.replace('<section aria-labelledby="h-fix">', section + '<section aria-labelledby="h-fix">')
t = t.replace('Not committed or merged yet.', 'Committed and pushed for review (PR #52), not merged yet.')
p.write_text(t, encoding='utf-8')
print(n_ap, len(latest))
