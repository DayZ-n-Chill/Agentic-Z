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
