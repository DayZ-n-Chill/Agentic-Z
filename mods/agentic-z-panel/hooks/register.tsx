import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { PanelRun, PanelStatus } from '../types'

// One pane with the DayZ state and buttons that run Agentic-Z's skill scripts
// directly. Nothing here asks the model for anything, so these cost no tokens.
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

// The clone that holds cwd: cwd itself or the nearest parent with Agentic-Z's
// skills, so a session started in a subfolder (workspace\MyVest) still finds it.
async function findClone($: any, cwd: string): Promise<string | null> {
  let dir = cwd.replace(/\//g, '\\').replace(/\\+$/, '')
  while (dir) {
    if (await $.fs.exists(join(dir, '.claude', 'skills', 'dayz-preflight', 'preflight.py'))) return dir
    const cut = dir.lastIndexOf('\\')
    if (cut < 0) return null
    dir = dir.slice(0, cut)
  }
  return null
}

// Agentic-Z lives in the project itself (a clone) or in the plugin cache.
async function findRoot($: any, cwd: string): Promise<string | null> {
  const clone = await findClone($, cwd)
  if (clone) return clone
  const home = (await $.process.run(['cmd', '/c', 'echo %USERPROFILE%'])).stdout.trim()
  const cache = join(home, '.claude', 'plugins', 'cache', 'dayz-n-chill', 'agentic-z')
  if (!(await $.fs.exists(cache))) return null
  // Numeric order, so 1.10.0 sorts after 1.9.0.
  const versions = (await $.fs.list(cache))
    .filter((v: { kind: string }) => v.kind === 'dir')
    .map((v: { name: string }) => v.name)
    .sort((a: string, b: string) => a.localeCompare(b, undefined, { numeric: true }))
  return versions.length ? join(cache, versions[versions.length - 1]) : null
}

async function activeMod($: any, cwd: string): Promise<string | null> {
  const file = join((await findClone($, cwd)) ?? cwd, '.claude', 'local-memory', 'dayz-init-state.json')
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
    $.process.run(['tasklist', '/FI', 'IMAGENAME eq DayZDiag_x64.exe', '/NH']),
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

async function runNow($: any, cwd: string, action: string, question?: string) {
  const current = (await read($, status)) ?? (await refresh($, cwd))
  if (!current.root) {
    $.ui.toast('Agentic-Z not found in this project or the plugin cache.')
    return
  }
  let argv: string[]
  if (action === 'stop') {
    argv = ['cmd', '/c', join(current.root, '.claude', 'skills', 'dayz-stop-test', 'stop_test.bat')]
  } else {
    const [skill, script] = SKILL[action as keyof typeof SKILL]
    argv = ['python', join(current.root, '.claude', 'skills', skill, script)]
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
    const result = await $.process.run(argv, { cwd, timeoutMs: 600_000 })
    const lines = (result.stdout + '\n' + result.stderr).trim().split(/\r?\n/)
    const failLine = lines.find((l: string) => l.startsWith('[FAIL]'))
    // An answer is the verdict and its citations; everything else is one line.
    const detail =
      action === 'ask'
        ? lines.filter((l: string) => /^(EVIDENCE|NONE|ERROR|\[\d+\])/.test(l)).slice(0, 6).join('\n')
        : (failLine ?? lines[lines.length - 1] ?? '')
    run = { action, ok: result.exitCode === 0, detail }
  } catch (err) {
    run = { action, ok: false, detail: String(err) }
  }
  await update($, lastRun, () => run)
  $.ui.toast(`${action}: ${run.ok ? 'done' : 'failed'}`)
  await refresh($, cwd)
}

export const register: Register = on => {
  let cwd = '.'

  on('session.start', async ($, e, next) => {
    cwd = e.cwd
    await $.command.register({ name: 'dayz-panel', description: 'Open the Agentic-Z panel' })
    void refresh($, cwd)
    return next(e)
  })

  on('command.run', { command: 'dayz-panel' }, async $ => {
    await refresh($, cwd)
    await $.ui.open({ id: PANE, title: 'Agentic-Z' })
    return { text: 'Agentic-Z panel opened.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Input, Text } = $.ui.resolve(e)
    const s = await read($, status)
    const run = await read($, lastRun)
    const working = await read($, busy)
    const press = (action: string) => () => runAction($, cwd, action)

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text>P: drive: {s?.isPMounted ? 'mounted' : 'not mounted'}</Text>
          <Text>Active mod: {s?.mod ?? 'none (run /dayz-init)'}</Text>
          <Text>Test session: {s?.isDiagRunning ? 'running' : 'stopped'}</Text>
          {!s?.root && <Text dimColor>Agentic-Z not found here.</Text>}
        </Box>
        <Box flexDirection="column">
          <Button key="mount" label="Mount P:" hotkey="p" onPress={press('mount')} />
          <Button key="build" label="Build PBO" hotkey="b" onPress={press('build')} />
          <Button key="gatebuild" label="Check build (PASS/FAIL)" hotkey="c" onPress={press('gatebuild')} />
          <Button key="gateingame" label="Check in game (PASS/FAIL)" hotkey="g" onPress={press('gateingame')} />
          <Button key="deploy" label="Deploy prebuilt PBOs" hotkey="d" onPress={press('deploy')} />
          <Button key="launch" label="Launch test" hotkey="l" onPress={press('launch')} />
          <Button key="stop" label="Stop test" hotkey="s" onPress={press('stop')} />
          <Button key="workbench" label="Open Workbench" hotkey="w" onPress={press('workbench')} />
          <Button key="objectbuilder" label="Open Object Builder" hotkey="o" onPress={press('objectbuilder')} />
          <Button key="logwatch" label="Check test logs" hotkey="t" onPress={press('logwatch')} />
          <Button key="health" label="Health page" hotkey="h" onPress={press('health')} />
          <Button key="releasepack" label="Release pack" hotkey="k" onPress={press('releasepack')} />
          <Button key="refresh" label="Refresh" hotkey="r" onPress={() => refresh($, cwd)} />
        </Box>
        {Input && (
          <Input
            key="ask"
            label="Ask vanilla:"
            placeholder="how does food spoil"
            submitLabel="ask"
            onSubmit={(question: string) => runAction($, cwd, 'ask', question)}
          />
        )}
        {working && <Text dimColor>Running {working}...</Text>}
        {run && (
          <Text dimColor>
            Last: {run.action} {run.ok ? 'done' : 'failed'} {run.detail}
          </Text>
        )}
      </Box>
    )
  })
}
