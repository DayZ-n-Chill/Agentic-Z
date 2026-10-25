import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { PanelRun, PanelStatus } from '../types'

// One pane with the DayZ state and buttons that run Agentic-Z's skill scripts
// directly. The buttons cost no tokens; only the ask field calls the model, to
// turn the cited vanilla code into a plain-English answer.
const PANE = 'agentic-z'
const status = atom({ plugin: 'agentic-z-panel', key: 'status' } as const, null)
const lastRun = atom({ plugin: 'agentic-z-panel', key: 'lastRun' } as const, null)
const busy = atom({ plugin: 'agentic-z-panel', key: 'busy' } as const, null)

const SKILL = {
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
} as const

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

const EXPLAIN_SYSTEM = `You explain how vanilla DayZ works to a mod author, using only the cited Enforce Script and config excerpts you are given.
Answer in plain English first: what happens, when, and why, as a short overview and then the key steps or numbers.
Name the classes, methods and constants that matter in backticks, and cite where each fact comes from as [n] (path:line) using the citation numbers given.
If the excerpts do not cover part of the question, say so plainly instead of guessing.
Use short markdown sections or bullets. Keep it under 300 words.`

// The excerpts can be long; the model needs the evidence, not all of it.
const EXPLAIN_EVIDENCE_CHARS = 40_000

// Turns ask.py's citations into an answer, or null when the model gave none:
// the citations still show, so a failed call loses nothing.
async function explain($: any, question: string, evidence: string): Promise<{ answer?: string; why?: string }> {
  try {
    const result = await $.model.complete({
      model: 'sonnet',
      system: EXPLAIN_SYSTEM,
      prompt: `Question: ${question}\n\nEvidence from /dayz-ask:\n${evidence.slice(0, EXPLAIN_EVIDENCE_CHARS)}`,
      maxTokens: 1500,
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
    if (action === 'ask') {
      if (!question?.trim()) {
        $.ui.toast('Type a question about vanilla DayZ first.')
        return
      }
      argv.push(question.trim())
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
    const result = await $.process.run(argv, { cwd, timeoutMs: 600_000, env: { PYTHONIOENCODING: 'utf-8' } })
    const lines = (result.stdout + '\n' + result.stderr).trim().split(/\r?\n/)
    const failLine = lines.find((l: string) => l.startsWith('[FAIL]'))
    // An answer is the verdict, its reason or notes (the lines indented two
    // spaces under it) and the citation headers; everything else is one line.
    const detail =
      action === 'ask'
        ? lines.filter((l: string) => /^(EVIDENCE|NONE|ERROR|\[\d+\]| {2}\S)/.test(l)).slice(0, 8).join('\n')
        : (failLine ?? lines[lines.length - 1] ?? '')
    // ask.py exits 1 for NONE: the search worked and found nothing.
    const nothingFound = action === 'ask' && result.exitCode === 1
    const ok = result.exitCode === 0 || nothingFound
    run = { action, ok, outcome: nothingFound ? 'nothing found' : ok ? 'done' : 'failed', detail }
    if (action === 'ask' && result.exitCode === 0) {
      await update($, busy, () => 'ask (writing the answer)')
      const { answer, why } = await explain($, question!.trim(), result.stdout)
      run = answer ? { ...run, answer } : { ...run, detail: `(no explanation: ${why})\n${detail}` }
    }
  } catch (err) {
    run = { action, ok: false, outcome: 'failed', detail: String(err) }
  }
  await update($, lastRun, () => run)
  $.ui.toast(`${action}: ${run.outcome}`)
  await refreshQuietly($, cwd)
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
    return next(e)
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
    return { text: lines.join('\n') }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Input, Markdown, Text } = $.ui.resolve(e)
    const s = await read($, status)
    const run = await read($, lastRun)
    const working = await read($, busy)
    const press = (action: string) => () => runAction($, cwd, action)

    // A titled card; the terminal draws it as a rounded frame, the app as a panel.
    const card = (title: string, children: any, borderColor = 'subtle') => (
      <Box flexDirection="column" borderStyle="round" borderColor={borderColor} paddingX={1}>
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
            <Input
              key="ask"
              label="Question:"
              placeholder="how does food spoil"
              submitLabel="ask"
              onSubmit={(question: string) => runAction($, cwd, 'ask', question)}
            />,
          )}
        {run &&
          card(
            run.ok ? `✓ ${run.action}: ${run.outcome}` : `✗ ${run.action}: ${run.outcome}`,
            run.answer ? (
              <Markdown key="answer" text={run.answer} />
            ) : (
              <Text dimColor>
                Last: {run.action} {run.outcome} {run.detail}
              </Text>
            ),
            runColor,
          )}
      </Box>
    )
  })
}
