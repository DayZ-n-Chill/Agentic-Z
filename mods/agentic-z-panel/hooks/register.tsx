import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { AskSettings, PanelRun, PanelStatus } from '../types'

// One pane with the DayZ state and buttons that run Agentic-Z's skill scripts
// directly. The buttons cost no tokens; only the ask field calls the model, to
// turn the cited vanilla code into a plain-English answer.
const PANE = 'agentic-z'
const status = atom({ plugin: 'agentic-z-panel', key: 'status' } as const, null)
const lastRun = atom({ plugin: 'agentic-z-panel', key: 'lastRun' } as const, null)
const busy = atom({ plugin: 'agentic-z-panel', key: 'busy' } as const, null)
const newVersion = atom({ plugin: 'agentic-z-panel', key: 'newVersion' } as const, null)
const askSettings = atom({ plugin: 'agentic-z-panel', key: 'askSettings' } as const, {
  topK: '10',
  excerptLines: '60',
  words: '400',
})

const SKILL = {
  preflight: ['dayz-preflight', 'preflight.py'],
  newmod: ['dayz-new-mod', 'new_mod.py'],
  importmod: ['dayz-import-mod', 'import_mod.py'],
  addserver: ['dayz-add-server', 'add_server.py'],
  mount: ['dayz-workdrive', 'mount.py'],
  build: ['dayz-build-pbo', 'build.py'],
  deploy: ['dayz-deploy-pbo', 'deploy.py'],
  gatebuild: ['dayz-gate', 'gate.py'],
  gateingame: ['dayz-gate', 'gate.py'],
  launch: ['dayz-launch-test', 'launch.py'],
  workbench: ['dayz-launch-workbench', 'launch.py'],
  objectbuilder: ['dayz-launch-objectbuilder', 'launch.py'],
  logwatch: ['dayz-logwatch', 'logwatch.py'],
  releasepack: ['dayz-release-pack', 'release_pack.py'],
  health: ['dayz-health', 'health.py'],
  ask: ['dayz-ask', 'ask.py'],
  deepdive: ['dayz-ask', 'ask.py'],
} as const

// What a person may pick before an ask. The lists are the limits: more
// sources, longer excerpts and longer answers are slower and cost more tokens,
// so the top of each list is as far as an ask goes. Deep dive is that top.
const ASK_CHOICES = {
  topK: [
    { value: '5', label: '5' },
    { value: '10', label: '10' },
    { value: '15', label: '15' },
    { value: '20', label: '20' },
    { value: '25', label: '25 (most)' },
  ],
  excerptLines: [
    { value: '60', label: '60 lines' },
    { value: '100', label: '100 lines' },
    { value: '150', label: '150 lines' },
    { value: '200', label: '200 lines (most)' },
  ],
  words: [
    { value: '300', label: 'Short' },
    { value: '400', label: 'Normal' },
    { value: '900', label: 'Long' },
  ],
} as const
const ASK_DEFAULTS: AskSettings = { topK: '10', excerptLines: '60', words: '400' }
const DEEP_DIVE: AskSettings = { topK: '25', excerptLines: '200', words: '900' }
const STORE_KEY = 'askSettings'
const isAsk = (action: string) => action === 'ask' || action === 'deepdive'

// A stored pick from an older version may no longer be on the list: each field
// off the list goes back to its default.
const allowed = (saved: any): AskSettings => {
  const pick = (field: keyof AskSettings) =>
    ASK_CHOICES[field].some(o => o.value === saved?.[field]) ? saved[field] : ASK_DEFAULTS[field]
  return { topK: pick('topK'), excerptLines: pick('excerptLines'), words: pick('words') }
}

// The map the "Add test server" button sets up; /dayz-add-server takes others.
const DEFAULT_SERVER = 'chernarus'

// "MyVest" or, for a first mod with no cached author, "MyVest by YourName".
const NEW_MOD_INPUT = /^(\S+)(?:\s+by\s+(.+))?$/i

// How far back the logs button reads, and how long it then watches. A button
// must return, so it reads the recent session lines once instead of following.
const LOGWATCH_SINCE_MINUTES = '30'
const LOGWATCH_SECONDS = '3'

const join = (...parts: string[]) => parts.join('\\')

const trimPath = (p: string) => p.replace(/\//g, '\\').replace(/\\+$/, '')

// cwd itself or the nearest parent that holds the given path, so a session
// started in a subfolder (workspace\MyVest) still finds the project. The walk
// stops before `stop` (and returns null) when one is given.
async function findUp($: any, cwd: string, rel: string, stop?: string): Promise<string | null> {
  let dir = trimPath(cwd)
  const stopAt = stop ? trimPath(stop).toLowerCase() : null
  while (dir) {
    if (stopAt && dir.toLowerCase() === stopAt) return null
    if (await $.fs.exists(join(dir, rel))) return dir
    const cut = dir.lastIndexOf('\\')
    if (cut < 0) return null
    dir = dir.slice(0, cut)
  }
  return null
}

// The clone that holds cwd: the nearest folder with Agentic-Z's skills.
const findClone = ($: any, cwd: string) => findUp($, cwd, join('.claude', 'skills', 'dayz-preflight', 'preflight.py'))

const homeDir = async ($: any): Promise<string> =>
  (await $.process.run(['cmd', '/c', 'echo %USERPROFILE%'])).stdout.trim()

// Agentic-Z lives in the project itself (a clone) or in the plugin cache.
async function findRoot($: any, cwd: string): Promise<string | null> {
  const clone = await findClone($, cwd)
  if (clone) return clone
  const home = await homeDir($)
  const cache = join(home, '.claude', 'plugins', 'cache', 'dayz-n-chill', 'agentic-z')
  if (!(await $.fs.exists(cache))) return null
  // Numeric order, so 1.10.0 sorts after 1.9.0.
  const versions = (await $.fs.list(cache))
    .filter((v: { kind: string }) => v.kind === 'dir')
    .map((v: { name: string }) => v.name)
    .sort((a: string, b: string) => a.localeCompare(b, undefined, { numeric: true }))
  return versions.length ? join(cache, versions[versions.length - 1]) : null
}

// The state file of the clone, or with no clone (a plugin install) of the
// nearest folder at or above cwd that has one. Like dayz-init's state.py, the
// walk stops before the home folder: ~\.claude is Claude Code's user config,
// not a project, and the scripts ignore a state file there.
async function activeMod($: any, cwd: string): Promise<string | null> {
  const state = join('.claude', 'local-memory', 'dayz-init-state.json')
  const project = (await findClone($, cwd)) ?? (await findUp($, cwd, state, await homeDir($)))
  if (!project) return null
  const file = join(project, state)
  if (!(await $.fs.exists(file))) return null
  try {
    return JSON.parse(await $.fs.read(file))?.last_intent?.mod_name ?? null
  } catch {
    return null
  }
}

async function refresh($: any, cwd: string): Promise<PanelStatus> {
  const [root, mod, isPMounted, tasks] = await Promise.all([
    findRoot($, cwd),
    activeMod($, cwd),
    $.fs.exists('P:\\'),
    // A failed tasklist call means the session state is unknown, not an error.
    $.process.run(['tasklist', '/FI', 'IMAGENAME eq DayZDiag_x64.exe', '/NH']).catch(() => ({ stdout: '' })),
  ])
  const next: PanelStatus = {
    root,
    mod,
    isPMounted,
    isDiagRunning: tasks.stdout.includes('DayZDiag_x64.exe'),
    checkedAt: await $.clock.now(),
  }
  await update($, status, () => next)
  return next
}

// One action at a time: a second press would start a second AddonBuilder run
// or a second DayZ session beside the first. The lock is checked and taken
// before any await, so two quick presses cannot both get past it; the busy
// atom only drives the "Running..." line in the pane.
let running: string | null = null

async function runAction($: any, cwd: string, action: string, question?: string) {
  if (running) {
    $.ui.toast(`${running} is still running`)
    return
  }
  running = action
  try {
    await update($, busy, () => action)
    await runNow($, cwd, action, question)
  } finally {
    running = null
    await update($, busy, () => null)
  }
}

const explainSystem = (words: number) => `You explain how vanilla DayZ works to a mod author, using only the cited Enforce Script and config excerpts you are given.
Answer in plain English first: what happens, when, and why, as a short overview and then the key steps or numbers.
Name the classes, methods and constants that matter in backticks, and cite where each fact comes from as [n] (path:line) using the citation numbers given.
If the excerpts do not cover part of the question, say so plainly instead of guessing.
Use short markdown sections or bullets. Keep it under ${words} words.`

// Turns ask.py's citations into an answer, or null when the model gave none:
// the citations still show, so a failed call loses nothing. The excerpts can be
// long; the model needs the evidence, not all of it.
async function explain($: any, settings: AskSettings, question: string, evidence: string): Promise<{ answer?: string; why?: string }> {
  const words = Number(settings.words)
  const evidenceChars = Math.min(150_000, Number(settings.topK) * Number(settings.excerptLines) * 100)
  try {
    const result = await $.model.complete({
      model: 'sonnet',
      system: explainSystem(words),
      prompt: `Question: ${question}\n\nEvidence from /dayz-ask:\n${evidence.slice(0, evidenceChars)}`,
      maxTokens: words * 5,
    })
    if (result.isAnswered) return { answer: result.text.trim() }
    return { why: [result.reason, result.status, result.error].filter(Boolean).join(' ') }
  } catch (err) {
    return { why: String(err) }
  }
}

const PYTHON_MISSING ='Python 3 not found: install it from python.org or add python/py to PATH'

// The interpreter the scripts\dayz wrappers use: python when it runs, else the py
// launcher. Running it, not just finding it, skips the Microsoft Store alias,
// which is on PATH but fails.
async function findPython($: any): Promise<string | null> {
  for (const exe of ['python', 'py']) {
    try {
      if ((await $.process.run([exe, '-c', ''], { timeoutMs: 15_000 })).exitCode === 0) return exe
    } catch {
      // not on PATH: try the next one
    }
  }
  return null
}

async function runNow($: any, cwd: string, action: string, question?: string) {
  // Read the state afresh: /dayz-init may have run since the pane last refreshed.
  let current: PanelStatus
  try {
    current = await refresh($, cwd)
  } catch (err) {
    await update($, lastRun, () => ({ action, ok: false, outcome: 'failed', detail: `status check failed: ${err}` }))
    $.ui.toast(`${action}: failed (status check: ${err})`)
    return
  }
  if (!current.root) {
    $.ui.toast('Agentic-Z not found in this project or the plugin cache.')
    return
  }
  let argv: string[]
  let settings: AskSettings | undefined
  if (action === 'stop') {
    argv = ['cmd', '/c', join(current.root, '.claude', 'skills', 'dayz-stop-test', 'stop_test.bat')]
  } else {
    const [skill, script] = SKILL[action as keyof typeof SKILL]
    const python = await findPython($)
    if (!python) {
      await update($, lastRun, () => ({ action, ok: false, outcome: 'failed', detail: PYTHON_MISSING }))
      $.ui.toast(`${action}: failed (${PYTHON_MISSING})`)
      return
    }
    argv = [python, join(current.root, '.claude', 'skills', skill, script)]
    if (action === 'gatebuild') argv.push('build')
    if (action === 'gateingame') argv.push('ingame')
    const needsMod = ['build', 'deploy', 'gatebuild', 'gateingame', 'launch', 'releasepack', 'health'].includes(action)
    if (isAsk(action)) {
      if (!question?.trim()) {
        $.ui.toast('Type a question about vanilla DayZ first.')
        return
      }
      settings = action === 'deepdive' ? DEEP_DIVE : await read($, askSettings)
      argv.push('--top-k', settings.topK, '--excerpt-lines', settings.excerptLines, question.trim())
    } else if (action === 'newmod') {
      const match = question?.trim().match(NEW_MOD_INPUT)
      if (!match) {
        $.ui.toast('Type a mod name, such as MyVest (first mod: MyVest by YourName).')
        return
      }
      argv.push(match[1])
      if (match[2]) argv.push('--author', match[2].trim())
    } else if (action === 'importmod') {
      if (!question?.trim()) {
        $.ui.toast('Type the mod folder path or a GitHub link first.')
        return
      }
      argv.push('--source', question.trim())
    } else if (action === 'addserver') {
      argv.push(DEFAULT_SERVER)
    } else if (action === 'logwatch') {
      argv.push('--since', LOGWATCH_SINCE_MINUTES, '--duration', LOGWATCH_SECONDS)
      if (current.mod) argv.push('--mod', current.mod)
    } else if (needsMod) {
      if (!current.mod) {
        $.ui.toast('No active mod yet. Run /dayz-init first.')
        return
      }
      argv.push(current.mod)
    } else if (action === 'workbench' && current.mod) {
      argv.push('--mod', current.mod)
    }
  }
  let run: PanelRun
  try {
    // Captured output is a pipe, where Python on Windows writes cp1252: a vanilla
    // line with a character such as U+2192 would crash the script mid-answer.
    // A working folder that no longer exists (a removed worktree, say) makes the
    // spawn fail with ENOENT naming the program, so fall back to the Agentic-Z root.
    const runCwd = (await $.fs.exists(cwd)) ? cwd : current.root
    const result = await $.process.run(argv, { cwd: runCwd, timeoutMs: 600_000, env: { PYTHONIOENCODING: 'utf-8' } })
    const lines = (result.stdout + '\n' + result.stderr).trim().split(/\r?\n/)
    const failLine = lines.find((l: string) => l.startsWith('[FAIL]'))
    // An answer is the verdict, its reason or notes (the lines indented two
    // spaces under it) and the citation headers; everything else is one line.
    const detail = isAsk(action)
      ? lines.filter((l: string) => /^(EVIDENCE|NONE|ERROR|\[\d+\]| {2}\S)/.test(l)).slice(0, 8).join('\n')
      : (failLine ?? lines[lines.length - 1] ?? '')
    // ask.py exits 1 for NONE: the search worked and found nothing.
    const nothingFound = isAsk(action) && result.exitCode === 1
    const ok = result.exitCode === 0 || nothingFound
    run = { action, ok, outcome: nothingFound ? 'nothing found' : ok ? 'done' : 'failed', detail }
    if (isAsk(action)) run.question = question!.trim()
    if (isAsk(action) && result.exitCode === 0) {
      await update($, busy, () => `${action} (writing the answer)`)
      const { answer, why } = await explain($, settings!, question!.trim(), result.stdout)
      run = answer ? { ...run, answer } : { ...run, detail: `(no explanation: ${why})\n${detail}` }
    }
  } catch (err) {
    run = { action, ok: false, outcome: 'failed', detail: String(err) }
  }
  await update($, lastRun, () => run)
  $.ui.toast(`${action}: ${run.outcome}`)
  await refreshQuietly($, cwd)
}

// Hands the answer to the main conversation, which can read whole files and
// take follow-up questions. It fills the prompt box rather than sending, so the
// person adds their own follow-up first.
async function continueInChat($: any, run: NonNullable<PanelRun>) {
  const text =
    `Explain in more depth how vanilla DayZ handles this: ${run.question}\n\n` +
    `The Agentic-Z panel's short answer, from /dayz-ask citations:\n\n${run.answer}\n\n` +
    'Read the cited vanilla files in full, with /dayz-ask or the dayz-rag tools for anything more, ' +
    'and fill in what the short answer could not cover.'
  const filled = await $.prompt.fill({ text })
  $.ui.toast(filled.isFilled ? 'Added to the prompt box: add your follow-up and press Enter.' : 'Could not fill the prompt box.')
}

// The marketplace's own list, so the panel can tell its users a newer version
// is out; a plugin install does not update itself unless auto-update is on.
const MARKETPLACE_URL = 'https://raw.githubusercontent.com/DayZ-n-Chill/Agentic-Z/main/.claude-plugin/marketplace.json'
const UPDATE_COMMAND = 'claude plugin update agentic-z-panel@dayz-n-chill'

// The newer version the marketplace lists, or null. Offline, a bad reply or a
// local copy newer than main all mean no notice, never an error.
async function checkForUpdate($: any) {
  try {
    const mine = JSON.parse(await $.fs.read(join(trimPath($.plugin.root), '.claude-plugin', 'plugin.json'))).version
    const res = await $.http.fetch(MARKETPLACE_URL)
    if (!res.ok) return
    const latest = JSON.parse(res.text).plugins?.find((p: { name: string }) => p.name === 'agentic-z-panel')?.version
    if (!latest || latest.localeCompare(mine, undefined, { numeric: true }) <= 0) return
    await update($, newVersion, () => latest)
    $.ui.toast(`Agentic-Z panel ${latest} is out: run ${UPDATE_COMMAND}`)
  } catch {
    // no notice
  }
}

// A status refresh nobody waits on must not throw: a failed process call
// would otherwise be an unhandled rejection.
const refreshQuietly = ($: any, cwd: string) => refresh($, cwd).catch(() => null)

export const register: Register = on => {
  let cwd = '.'

  on('session.start', async ($, e, next) => {
    cwd = e.cwd
    await $.command.register({ name: 'dayz-panel', description: 'Open the Agentic-Z panel' })
    void refreshQuietly($, cwd)
    void checkForUpdate($)
    // The last picks carry over to the next session.
    void $.store
      .get(STORE_KEY)
      .then((saved: unknown) => update($, askSettings, () => allowed(saved)))
      .catch(() => null)
    // Every session opens the panel itself: nobody should have to type
    // /dayz-panel to get it. A narrow terminal holds it until there is room.
    void $.ui.open({ id: PANE, title: 'Agentic-Z' }).catch(() => null)
    return next(e)
  })

  // One click above the prompt opens the pane, so nobody has to type /dayz-panel.
  // It steps aside while a survey uses the band.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const { Box, Button } = $.ui.resolve(e)
    return (
      <Box key="open-panel">
        <Button
          key="open-panel"
          label="Agentic-Z panel"
          plain
          dimColor
          hover={{ backgroundColor: 'subtle' }}
          onPress={async () => {
            await refreshQuietly($, cwd)
            await $.ui.open({ id: PANE, title: 'Agentic-Z' })
          }}
        />
      </Box>
    )
  })

  on('command.run', { command: 'dayz-panel' }, async $ => {
    const s = await refresh($, cwd)
    const run = await read($, lastRun)
    await $.ui.open({ id: PANE, title: 'Agentic-Z' })
    const lines = [
      'Agentic-Z panel opened.',
      `  P: drive      ${s.isPMounted ? 'mounted' : 'not mounted (press p in the panel)'}`,
      `  Active mod    ${s.mod ?? 'none (run /dayz-init)'}`,
      `  Test session  ${s.isDiagRunning ? 'running' : 'stopped'}`,
      `  Agentic-Z     ${s.root ?? 'not found in this project or the plugin cache'}`,
    ]
    if (run) lines.push(`  Last run      ${run.action} ${run.outcome}`)
    const latest = await read($, newVersion)
    if (latest) lines.push(`  Update        ${latest} is out: run ${UPDATE_COMMAND}, then restart`)
    return { text: lines.join('\n') }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Input, Markdown, Select, Text } = $.ui.resolve(e)
    const s = await read($, status)
    const run = await read($, lastRun)
    const picks = await read($, askSettings)
    const choose = (field: keyof AskSettings) => async (value: string) => {
      const next = allowed({ ...picks, [field]: value })
      await update($, askSettings, () => next)
      await $.store.set(STORE_KEY, next)
    }
    const working = await read($, busy)
    const latest = await read($, newVersion)
    const press = (action: string) => () => runAction($, cwd, action)

    // A titled card; the terminal draws it as a rounded frame, the app as a panel.
    // A plain card's frame is dimmed so it groups without competing with the
    // buttons; the last run's green or red frame stays at full strength.
    const card = (title: string, children: any, borderColor = 'subtle') => (
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={borderColor}
        borderDimColor={borderColor === 'subtle'}
        paddingX={1}
      >
        <Text weight="bold" size="heading" color="claude">
          {title}
        </Text>
        {children}
      </Box>
    )
    // One status line with a colored dot: green when good, red when not.
    const light = (isGood: boolean, text: string) => (
      <Box flexDirection="row" gap={1}>
        <Text color={isGood ? 'success' : 'error'}>●</Text>
        <Text>{text}</Text>
      </Box>
    )
    // Plain buttons have no filled chrome, so a row of them reads as separate
    // controls instead of one gray block; each lights gray under the pointer
    // (its own hover scope). Plain draws the hotkey itself: "b: Build PBO".
    const btn = (action: string, label: string, hotkey: string, onPress = press(action)) => (
      <Button
        key={action}
        label={label}
        hotkey={hotkey}
        plain
        hover={{ scope: `btn-${action}`, backgroundColor: 'subtle' }}
        onPress={onPress}
      />
    )
    // A labelled row: the fixed-width label lines the rows of a card up, and
    // the buttons wrap under each other on a narrow pane.
    const row = (label: string, children: any) => (
      <Box flexDirection="row" columnGap={1}>
        <Box width={7} flexShrink={0}>
          <Text dimColor>{label}</Text>
        </Box>
        <Box flexDirection="row" flexWrap="wrap" flexGrow={1} columnGap={2} rowGap={1}>
          {children}
        </Box>
      </Box>
    )
    const rows = (children: any) => (
      <Box flexDirection="column" rowGap={1} paddingTop={1}>
        {children}
      </Box>
    )
    const runColor = !run ? 'subtle' : run.ok ? 'success' : 'error'

    return (
      <Box flexDirection="column" gap={1}>
        {latest && (
          <Box flexDirection="row" columnGap={2}>
            <Text color="suggestion">
              Panel {latest} is out: run {UPDATE_COMMAND}, then restart Claude Code.
            </Text>
            {btn('dismiss-update', 'Dismiss', 'u', () => update($, newVersion, () => null))}
          </Box>
        )}
        {card(
          'Status',
          <Box flexDirection="row" columnGap={2} alignItems="flex-start">
            <Box flexDirection="column" flexGrow={1}>
              {light(!!s?.isPMounted, `P: drive: ${s?.isPMounted ? 'mounted' : 'not mounted'}`)}
              {light(!!s?.mod, `Active mod: ${s?.mod ?? 'none (run /dayz-init)'}`)}
              {light(!!s?.isDiagRunning, `Test session: ${s?.isDiagRunning ? 'running' : 'stopped'}`)}
              {!s?.root && <Text color="warning">Agentic-Z not found here.</Text>}
            </Box>
            {btn('refresh', 'Refresh', 'r', () => refreshQuietly($, cwd))}
          </Box>,
        )}
        {working && <Text color="warning">⟳ Running {working}...</Text>}
        {card(
          'Start a project',
          rows([
            row('Setup', [
              btn('preflight', 'Check setup', 'e'),
              btn('addserver', `Add test server (${DEFAULT_SERVER})`, 'v'),
            ]),
            Input && (
              <Input
                key="newmod"
                label="New mod:"
                placeholder="MyVest (first mod: MyVest by YourName)"
                submitLabel="create"
                onSubmit={(text: string) => runAction($, cwd, 'newmod', text)}
              />
            ),
            Input && (
              <Input
                key="importmod"
                label="Import mod:"
                placeholder="folder path or GitHub link"
                submitLabel="import"
                onSubmit={(text: string) => runAction($, cwd, 'importmod', text)}
              />
            ),
          ]),
        )}
        {card(
          'Build and test',
          rows([
            row('Build', [
              btn('build', 'Build PBO', 'b'),
              btn('gatebuild', 'Check build', 'c'),
              btn('deploy', 'Deploy prebuilt', 'd'),
            ]),
            row('Play', [
              btn('launch', 'Launch', 'l'),
              btn('gateingame', 'Check in game', 'g'),
              btn('stop', 'Stop', 's'),
              btn('logwatch', 'Logs', 't'),
            ]),
          ]),
        )}
        {card(
          'Tools',
          rows([
            row('Open', [
              btn('mount', 'Mount P:', 'p'),
              btn('workbench', 'Workbench', 'w'),
              btn('objectbuilder', 'Object Builder', 'o'),
            ]),
            row('Ship', [btn('health', 'Health page', 'h'), btn('releasepack', 'Release pack', 'k')]),
          ]),
        )}
        {Input &&
          card(
            'Ask vanilla DayZ',
            <Box flexDirection="column" rowGap={1}>
              <Input
                key="ask"
                label="Question:"
                placeholder="how does food spoil"
                submitLabel="ask"
                onSubmit={(question: string) => runAction($, cwd, 'ask', question)}
              />
              {Select && (
                <Box flexDirection="row" flexWrap="wrap" columnGap={2} rowGap={1}>
                  <Select key="ask-topk" label="Sources:" options={ASK_CHOICES.topK} value={picks.topK} onSelect={choose('topK')} />
                  <Select
                    key="ask-lines"
                    label="Excerpt:"
                    options={ASK_CHOICES.excerptLines}
                    value={picks.excerptLines}
                    onSelect={choose('excerptLines')}
                  />
                  <Select key="ask-words" label="Answer:" options={ASK_CHOICES.words} value={picks.words} onSelect={choose('words')} />
                </Box>
              )}
            </Box>,
          )}
        {run &&
          card(
            run.ok ? `✓ ${run.action}: ${run.outcome}` : `✗ ${run.action}: ${run.outcome}`,
            <Box flexDirection="column" rowGap={1}>
              {run.answer ? (
                <Markdown key="answer" text={run.answer} />
              ) : (
                <Text dimColor>
                  Last: {run.action} {run.outcome} {run.detail}
                </Text>
              )}
              <Box flexDirection="row" flexWrap="wrap" columnGap={2} rowGap={1}>
                {run.answer && run.action === 'ask' &&
                  btn('deepdive', 'Deep dive', 'v', () => runAction($, cwd, 'deepdive', run.question))}
                {run.answer && btn('continue', 'Continue in chat', 'm', () => continueInChat($, run))}
                {btn('dismiss-run', 'Dismiss', 'x', () => update($, lastRun, () => null))}
              </Box>
            </Box>,
            runColor,
          )}
      </Box>
    )
  })
}
