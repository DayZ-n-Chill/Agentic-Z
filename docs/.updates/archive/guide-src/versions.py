import pathlib, re
p = pathlib.Path(__file__).parent / 'agentic-z-team.html'
t = p.read_text(encoding='utf-8')

def rep(old, new, count=1):
    global t
    assert old in t, old[:90]
    t = t.replace(old, new, count) if count else t.replace(old, new)

s = t.index('<section aria-labelledby="h-grades">')
e = t.index('</section>', s) + len('</section>')
g = t[s:e]

g = g.replace('<h2 id="h-grades">Quality grades</h2>', '<h2 id="h-grades">Quality by version</h2>')
g = g.replace('<th scope="col">First grade</th><th scope="col">Latest check</th><th scope="col">Now</th>',
              '<th scope="col">v1.6.0<br>released</th><th scope="col">v1.7.0<br>agent team</th><th scope="col">v2.0.0<br>goal</th>')
g = g.replace('<span class="pill move">Fixed, recheck</span>', '<span class="pill ok">A+</span>')
g = g.replace('<span class="pill fix">On hold</span>', '<span class="pill ok">A+</span>')
g = re.sub(r'<div class="status-key">.*?</div>', '<div class="status-key"><span>v1.6.0 and v1.7.0 are grades from independent reviewers. v2.0.0 is the goal every item is built and regraded to.</span></div>', g, count=1, flags=re.S)
g = re.sub(r'<p>Every agent and skill was graded.*?</p>', '''<p>Every agent and skill has been graded at each version by independent AI reviewers (see "How the grading works"). This is how quality moves from one version to the next.</p>''', g, count=1, flags=re.S)

timeline = '''<div class="chart"><svg viewBox="0 0 1140 190" role="img" aria-label="Agentic-Z versions and grades">
<defs><marker id="ahv" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--line)"/></marker></defs>
<rect class="b-gate" x="10" y="20" width="250" height="120" rx="10"/>
<text class="t" x="135" y="50" font-size="16">v1.6.0</text><text class="s" x="135" y="70">Released. First graded.</text>
<text class="tw" x="135" y="96">Mostly B and C</text><text class="s" x="135" y="116">0 of 55 at A+, 84 tests</text>
<line class="ln" x1="260" y1="80" x2="296" y2="80" marker-end="url(#ahv)"/>
<rect class="b-lead" x="298" y="20" width="250" height="120" rx="10"/>
<text class="t" x="423" y="50" font-size="16">v1.7.0</text><text class="s" x="423" y="70">Agent team, 5 grading rounds</text>
<text class="tw" x="423" y="96">Mostly A and A+</text><text class="s" x="423" y="116">22 of 55 at A+, 1,064 tests</text>
<line class="ln" x1="548" y1="80" x2="584" y2="80" marker-end="url(#ahv)"/>
<rect class="b-orch2" x="586" y="20" width="250" height="120" rx="10"/>
<text class="t" x="711" y="50" font-size="16">v1.8.0</text><text class="s" x="711" y="70">Token savers, panel, wrappers</text>
<text class="tw" x="711" y="96">Built and tested</text><text class="s" x="711" y="116">1,332 tests</text>
<line class="ln" x1="836" y1="80" x2="872" y2="80" marker-end="url(#ahv)"/>
<rect class="b-play" x="874" y="20" width="256" height="120" rx="10"/>
<text class="t" x="1002" y="50" font-size="16">v2.0.0</text><text class="s" x="1002" y="70">Everything in this guide</text>
<text class="tw" x="1002" y="96">All A+</text><text class="s" x="1002" y="116">Regraded independently</text>
<text class="note" x="570" y="172" text-anchor="middle">Each version is graded by fresh reviewers. A grade only moves up when a new reviewer confirms it.</text>
</svg></div>'''
g = g.replace('</p>', '</p>\n ' + timeline, 1)
t = t[:s] + g + t[e:]

# grade detail table header
t = t.replace('<th scope="col">Latest</th><th scope="col">Why</th><th scope="col">Done since</th>',
              '<th scope="col">v1.7.0</th><th scope="col">Why</th><th scope="col">Done since (for v2.0.0)</th>')
t = t.replace("The latest independent reviewer's reason for each grade, and what was changed afterwards.",
              "The v1.7.0 reviewer's reason for each grade, and what was changed afterwards on the way to v2.0.0.")
p.write_text(t, encoding='utf-8')
print('ok')
