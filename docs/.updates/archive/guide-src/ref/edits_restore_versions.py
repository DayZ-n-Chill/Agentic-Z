Y = '<td><span class="pill ok">Has</span></td>'
N = '<td><span class="pill todo">Does not have</span></td>'


def row(name, *cells):
    return '   <tr><th scope="row">%s</th>%s</tr>\n' % (name, ''.join(cells))


def grp(name):
    return '   <tr class="grp"><th colspan="4" scope="colgroup">%s</th></tr>\n' % name


def num(*v):
    return ''.join('<td>%s</td>' % x for x in v)


body = (grp('Counts')
        + row('Agents', num('14', '21', '30'))
        + row('Skills', num('29', '31', '44'))
        + row('Hooks', num('0', '0', '3'))
        + row('Tests', num('84', '1,064', '2,884 plus 18 panel tests'))
        + grp('Agents')
        + row('Workers for script, config, models, textures, UI, maps, server and Workbench', Y, Y, Y)
        + row('<code>dayz-mod-reviewer</code> and <code>dayz-mod-debugger</code>', Y, Y, Y)
        + row('Figma-to-DayZ pipeline: three agents and its rules file', Y, Y, Y)
        + row('<code>agent-creator</code>', Y, Y, Y)
        + row('Orchestrator, architect and team leads', N, Y, Y)
        + row('<code>dayz-build-engineer</code> and <code>dayz-docs-writer</code>', N, Y, Y)
        + row('<code>dayz-build-checker</code> and <code>dayz-ingame-tester</code>', N, Y, Y)
        + row('<code>dayz-router</code> and <code>/dayz-route</code>', N, N, Y)
        + row('Eight domain specialists with knowledge packs', N, N, Y)
        + grp('Checks')
        + row('<code>/dayz-gate</code> build, in-game, behavior and visual gates as scripts, with known-error triage', N, N, Y)
        + row('<code>/dayz-lint</code> inside the build gate', N, N, Y)
        + row('Hooks: edit check, scope guard and paste-in router', N, N, Y)
        + row('Answer tests (evals)', N, N, Y)
        + row('<code>tests</code> workflow on every pull request', N, N, Y)
        + grp('Skills and tools')
        + row('<code>/dayz-deploy-pbo</code>', N, Y, Y)
        + row('<code>/dayz-record-correction</code>', N, Y, Y)
        + row('Workflow commands: recipe, log watch, release pack, server kit, upgrade guard, conflict check, balance, health, cited answers and layout preview', N, N, Y)
        + row('Token savers: status line, Tier 2 split into a core file and topic files', N, N, Y)
        + row('<code>agentic-z-panel</code> side panel', N, N, Y)
        + grp('Search')
        + row('<code>dayz-rag</code> search over vanilla DayZ source', Y, Y, Y)
        + row('Wiki search: <code>/dayz-search-wiki-index</code> and the <code>search_dayz_wiki</code> tool', Y, Y, N))

SECTIONS = {'h-fix': '''<section aria-labelledby="h-fix">
 <h2 id="h-fix">Version comparison</h2>
 <p>What each version has and does not have. Agent, skill and hook counts are from the repo at each version; test counts are the pytest totals recorded at each version.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Feature</th><th scope="col">v1.6.0<br>released</th><th scope="col">v1.7.0<br>agent team</th><th scope="col">v2.0.0<br>final</th></tr></thead>
  <tbody>
%s  </tbody>
 </table></div>
</section>''' % body}
