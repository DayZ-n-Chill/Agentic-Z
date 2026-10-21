import { expect, test } from 'claude-code/testing'

const PANE = {
  plugin: 'agentic-z-panel',
  component: 'Pane',
  requestId: 'agentic-z',
  props: {
    title: 'Agentic-Z',
    isFocused: false,
    bodyColumns: 50,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 20 },
    view: {},
  },
} as const

// Stands in for the engine: a clone at C:\proj with an active mod, P: mounted,
// DayZ not running. Every process call is recorded instead of run.
function engine(on: any, runs: string[][]) {
  const files: Record<string, string> = {
    'C:\\proj\\.claude\\skills\\dayz-preflight\\preflight.py': '',
    'C:\\proj\\.claude\\local-memory\\dayz-init-state.json': '{"last_intent": {"mod_name": "MyVest"}}',
    'P:\\': '',
  }
  on('command.register', () => ({ value: { command: 'dayz-panel' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.toast', () => ({ value: undefined }))
  on('session.start', (_: unknown, e: any) => ({ cwd: e.cwd }))
  on('fs.exists', (_: unknown, e: any) => ({ value: e.path in files }))
  on('fs.read', (_: unknown, e: any) => ({ value: files[e.path] }))
  on('clock.now', () => ({ value: 0 }))
  on('process.run', (_: unknown, e: any) => {
    runs.push(e.argv)
    return { value: { exitCode: 0, stdout: 'INFO: No tasks are running.', stderr: '' } }
  })
}

test('the pane shows the state and runs the build for the active mod', async ($, on) => {
  const runs: string[][] = []
  engine(on, runs)
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })

  for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /Active mod: MyVest/ }))?.text).toBe('Active mod: MyVest')
    expect((await ui.find({ type: 'Text', text: /P: drive/ }))?.text).toBe('P: drive: mounted')
    await ui.unmount()
  }

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(runs.some(argv => argv.join(' ') === 'python C:\\proj\\.claude\\skills\\dayz-build-pbo\\build.py MyVest')).toBe(true)
})

test('the gate buttons run /dayz-gate build and ingame for the active mod', async ($, on) => {
  const runs: string[][] = []
  engine(on, runs)
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'gatebuild' })
  await ui.press({ key: 'gateingame' })
  await ui.unmount()
  const lines = runs.map(argv => argv.join(' '))
  expect(lines).toContain('python C:\\proj\\.claude\\skills\\dayz-gate\\gate.py build MyVest')
  expect(lines).toContain('python C:\\proj\\.claude\\skills\\dayz-gate\\gate.py ingame MyVest')
})

test('the workflow buttons run logwatch, the health page and the release pack for the active mod', async ($, on) => {
  const runs: string[][] = []
  engine(on, runs)
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'logwatch' })
  await ui.press({ key: 'health' })
  await ui.press({ key: 'releasepack' })
  await ui.unmount()
  const lines = runs.map(argv => argv.join(' '))
  expect(lines).toContain('python C:\\proj\\.claude\\skills\\dayz-logwatch\\logwatch.py --since 30 --duration 3 --mod MyVest')
  expect(lines).toContain('python C:\\proj\\.claude\\skills\\dayz-health\\health.py MyVest')
  expect(lines).toContain('python C:\\proj\\.claude\\skills\\dayz-release-pack\\release_pack.py MyVest')
})

test('the ask field runs /dayz-ask with the question and skips an empty one', async ($, on) => {
  const runs: string[][] = []
  engine(on, runs)
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const asked = () => runs.filter(argv => argv.some(a => a.endsWith('ask.py')))
  await ui.input({ key: 'ask', text: '   ' })
  expect(asked().length).toBe(0)
  await ui.input({ key: 'ask', text: 'how does food spoil' })
  await ui.unmount()
  expect(asked().map(argv => argv.join(' '))).toEqual(['python C:\\proj\\.claude\\skills\\dayz-ask\\ask.py how does food spoil'])
})

// --- the rest of the buttons, the guards and the plugin-cache fallback ------------------

// A variant of engine() with the parts the tests below change: the files on
// disk, the plugin-cache folders, the toasts shown, and a process call that
// can be held open to stand for a long build.
function engineWith(on: any, runs: string[][], opts: {
  files?: Record<string, string>
  cacheDirs?: string[]
  toasts?: string[]
  hold?: (argv: string[]) => Promise<void> | undefined
} = {}) {
  const files: Record<string, string> = opts.files ?? {
    'C:\\proj\\.claude\\skills\\dayz-preflight\\preflight.py': '',
    'C:\\proj\\.claude\\local-memory\\dayz-init-state.json': '{"last_intent": {"mod_name": "MyVest"}}',
    'P:\\': '',
  }
  on('command.register', () => ({ value: { command: 'dayz-panel' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.toast', (_: unknown, e: any) => {
    opts.toasts?.push(e.text)
    return { value: undefined }
  })
  on('session.start', (_: unknown, e: any) => ({ cwd: e.cwd }))
  on('fs.exists', (_: unknown, e: any) => ({ value: e.path in files }))
  on('fs.read', (_: unknown, e: any) => ({ value: files[e.path] }))
  on('fs.list', () => ({
    value: (opts.cacheDirs ?? []).map(name => ({ name, kind: 'dir', size: 0, modifiedAt: 0 })),
  }))
  on('clock.now', () => ({ value: 0 }))
  on('process.run', async (_: unknown, e: any) => {
    runs.push(e.argv)
    if (e.argv.join(' ') === 'cmd /c echo %USERPROFILE%') {
      return { value: { exitCode: 0, stdout: 'C:\\Users\\me\r\n', stderr: '' } }
    }
    const held = opts.hold?.(e.argv)
    if (held) await held
    return { value: { exitCode: 0, stdout: 'INFO: No tasks are running.', stderr: '' } }
  })
}

async function openPane($: any) {
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  return $.ui.mount({ ...PANE, surface: 'terminal' })
}

const scriptRuns = (runs: string[][]) =>
  runs.map(argv => argv.join(' ')).filter(line => !line.startsWith('tasklist') && !line.startsWith('cmd /c echo'))

test('stop, mount, deploy, launch, workbench and object builder run their scripts', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs)
  const ui = await openPane($)
  for (const key of ['stop', 'mount', 'deploy', 'launch', 'workbench', 'objectbuilder']) await ui.press({ key })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([
    'cmd /c C:\\proj\\.claude\\skills\\dayz-stop-test\\stop_test.bat',
    'python C:\\proj\\.claude\\skills\\dayz-workdrive\\mount.py',
    'python C:\\proj\\.claude\\skills\\dayz-deploy-pbo\\deploy.py MyVest',
    'python C:\\proj\\.claude\\skills\\dayz-launch-test\\launch.py MyVest',
    'python C:\\proj\\.claude\\skills\\dayz-launch-workbench\\launch.py --mod MyVest',
    'python C:\\proj\\.claude\\skills\\dayz-launch-objectbuilder\\launch.py',
  ])
})

test('with no active mod, workbench opens bare and the mod buttons only toast', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, { toasts, files: { 'C:\\proj\\.claude\\skills\\dayz-preflight\\preflight.py': '' } })
  const ui = await openPane($)
  await ui.press({ key: 'workbench' })
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\.claude\\skills\\dayz-launch-workbench\\launch.py'])
  expect(toasts).toContain('No active mod yet. Run /dayz-init first.')
})

test('a second press while an action runs starts nothing', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  let ui: any
  let toastsDuringBuild: string[] = []
  // While build.py is still running, press Check in game; the build ends once that press is done.
  engineWith(on, runs, {
    toasts,
    hold: argv =>
      argv.some(a => a.endsWith('build.py'))
        ? ui.press({ key: 'gateingame' }).then(() => {
            toastsDuringBuild = [...toasts]
          })
        : undefined,
  })
  ui = await openPane($)
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(toastsDuringBuild).toEqual(['build is still running'])
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\.claude\\skills\\dayz-build-pbo\\build.py MyVest'])
  expect(toasts).toEqual(['build is still running', 'build: done'])
})

test('without a clone, the panel uses the newest plugin cache version by number', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs, {
    cacheDirs: ['1.9.0', '1.10.0', '1.2.0'],
    files: {
      'C:\\Users\\me\\.claude\\plugins\\cache\\dayz-n-chill\\agentic-z': '',
      'C:\\proj\\.claude\\local-memory\\dayz-init-state.json': '{"last_intent": {"mod_name": "MyVest"}}',
    },
  })
  const ui = await openPane($)
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([
    'python C:\\Users\\me\\.claude\\plugins\\cache\\dayz-n-chill\\agentic-z\\1.10.0\\.claude\\skills\\dayz-build-pbo\\build.py MyVest',
  ])
})

test('with Agentic-Z nowhere, the pane says so and a press only toasts', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, { toasts, files: {} })
  const ui = await openPane($)
  expect((await ui.find({ type: 'Text', text: /not found here/ }))?.text).toBe('Agentic-Z not found here.')
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([])
  expect(toasts).toContain('Agentic-Z not found in this project or the plugin cache.')
})
