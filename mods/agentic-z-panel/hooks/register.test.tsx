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
// DayZ not running, the installed panel 0.4.0 and the marketplace listing
// `listed`. Every process call is recorded instead of run.
function engine(on: any, runs: string[][], listed = '0.4.0', opened: string[] = []) {
  const files: Record<string, string> = {
    'C:\\proj\\skills\\dayz-preflight\\preflight.py': '',
    'C:\\proj\\.claude\\local-memory\\dayz-init-state.json': '{"last_intent": {"mod_name": "MyVest"}}',
    'P:\\': '',
  }
  on('command.register', () => ({ value: { command: 'dayz-panel' } }))
  on('ui.open', (_: unknown, e: any) => {
    opened.push(e.id)
    return { value: { isPlaced: true } }
  })
  on('ui.toast', () => ({ value: undefined }))
  on('session.start', (_: unknown, e: any) => ({ cwd: e.cwd }))
  on('fs.exists', (_: unknown, e: any) => ({ value: e.path in files }))
  on('fs.read', (_: unknown, e: any) => ({ value: e.path.endsWith('plugin.json') ? '{"version": "0.4.0"}' : files[e.path] }))
  on('http.fetch', () => ({
    value: { status: 200, ok: true, headers: {}, text: JSON.stringify({ plugins: [{ name: 'agentic-z-panel', version: listed }] }) },
  }))
  on('clock.now', () => ({ value: 0 }))
  on('process.run', (_: unknown, e: any) => {
    runs.push(e.argv)
    return { value: { exitCode: 0, stdout: 'INFO: No tasks are running.', stderr: '' } }
  })
}

test('/dayz-panel replies with the state, not just that it opened', async ($, on) => {
  engine(on, [])
  await $.session.start({ cwd: 'C:\\proj', surface: 'terminal', isInteractive: true })
  const reply = await $.command.run({ command: 'dayz-panel', args: '' })
  expect(reply.text).toContain('Agentic-Z panel opened.')
  expect(reply.text).toContain('P: drive      mounted')
  expect(reply.text).toContain('Active mod    MyVest')
  expect(reply.text).toContain('Test session  stopped')
  expect(reply.text).toContain('Agentic-Z     C:\\proj')
})

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
  expect(runs.some(argv => argv.join(' ') === 'python C:\\proj\\skills\\dayz-build-pbo\\build.py MyVest')).toBe(true)
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
  expect(lines).toContain('python C:\\proj\\skills\\dayz-gate\\gate.py build MyVest')
  expect(lines).toContain('python C:\\proj\\skills\\dayz-gate\\gate.py ingame MyVest')
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
  expect(lines).toContain('python C:\\proj\\skills\\dayz-logwatch\\logwatch.py --since 30 --duration 3 --mod MyVest')
  expect(lines).toContain('python C:\\proj\\skills\\dayz-health\\health.py MyVest')
  expect(lines).toContain('python C:\\proj\\skills\\dayz-release-pack\\release_pack.py MyVest')
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
  expect(asked().map(argv => argv.join(' '))).toEqual([
    'python C:\\proj\\skills\\dayz-ask\\ask.py --top-k 10 --excerpt-lines 60 how does food spoil',
  ])
})

// --- the rest of the buttons, the guards and the plugin-cache fallback ------------------

// A variant of engine() with the parts the tests below change: the files on
// disk, the plugin-cache folders, the toasts shown, a process call that can be
// held open to stand for a long build, and a result to return for a script.
function engineWith(on: any, runs: string[][], opts: {
  files?: Record<string, string>
  cacheDirs?: string[]
  toasts?: string[]
  hold?: (argv: string[]) => Promise<void> | undefined
  result?: (argv: string[]) => { exitCode: number; stdout: string; stderr: string } | undefined
  clockFails?: () => boolean
  seen?: (e: any) => void
} = {}) {
  const files: Record<string, string> = opts.files ?? {
    'C:\\proj\\skills\\dayz-preflight\\preflight.py': '',
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
  on('clock.now', () => {
    if (opts.clockFails?.()) throw new Error('clock gone')
    return { value: 0 }
  })
  on('process.run', async (_: unknown, e: any) => {
    runs.push(e.argv)
    opts.seen?.(e)
    if (e.argv.join(' ') === 'cmd /c echo %USERPROFILE%') {
      return { value: { exitCode: 0, stdout: 'C:\\Users\\me\r\n', stderr: '' } }
    }
    const held = opts.hold?.(e.argv)
    if (held) await held
    return { value: opts.result?.(e.argv) ?? { exitCode: 0, stdout: 'INFO: No tasks are running.', stderr: '' } }
  })
}

async function openPane($: any) {
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  return $.ui.mount({ ...PANE, surface: 'terminal' })
}

// The script runs alone: no status calls and no "python -c ''" interpreter probes.
const scriptRuns = (runs: string[][]) =>
  runs
    .filter(argv => argv[1] !== '-c')
    .map(argv => argv.join(' '))
    .filter(line => !line.startsWith('tasklist') && !line.startsWith('cmd /c echo'))

test('with only the py launcher, buttons run their script with py', async ($, on) => {
  // The B+ grade's defect: a hard-coded python failed every button but Stop on a py-only PC.
  const runs: string[][] = []
  engineWith(on, runs, {
    result: argv => (argv[0] === 'python' ? { exitCode: 9009, stdout: '', stderr: 'not found' } : undefined),
  })
  const ui = await openPane($)
  await ui.press({ key: 'deploy' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual(['py C:\\proj\\skills\\dayz-deploy-pbo\\deploy.py MyVest'])
})

test('with no Python at all, a button runs nothing and says how to fix it', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, {
    toasts,
    result: argv => (argv[1] === '-c' ? { exitCode: 9009, stdout: '', stderr: '' } : undefined),
  })
  const ui = await openPane($)
  await ui.press({ key: 'deploy' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([])
  expect(toasts).toContain('deploy: failed (Python 3 not found: install it from python.org or add python/py to PATH)')
})

test('scripts run with UTF-8 output, so a non-ASCII answer cannot crash them', async ($, on) => {
  // The B+ grade's defect: through a pipe Python wrote cp1252 and died on U+2192.
  const inits: any[] = []
  const runs: string[][] = []
  engineWith(on, runs, { seen: e => e.argv.some((a: string) => a.endsWith('.py')) && inits.push(e.init) })
  const ui = await openPane($)
  await ui.press({ key: 'deploy' })
  await ui.unmount()
  expect(inits.length).toBe(1)
  expect(inits[0].env).toEqual({ PYTHONIOENCODING: 'utf-8' })
})

test('stop, mount, deploy, launch, workbench and object builder run their scripts', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs)
  const ui = await openPane($)
  for (const key of ['stop', 'mount', 'deploy', 'launch', 'workbench', 'objectbuilder']) await ui.press({ key })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([
    'cmd /c C:\\proj\\skills\\dayz-stop-test\\stop_test.bat',
    'python C:\\proj\\skills\\dayz-workdrive\\mount.py',
    'python C:\\proj\\skills\\dayz-deploy-pbo\\deploy.py MyVest',
    'python C:\\proj\\skills\\dayz-launch-test\\launch.py MyVest',
    'python C:\\proj\\skills\\dayz-launch-workbench\\launch.py --mod MyVest',
    'python C:\\proj\\skills\\dayz-launch-objectbuilder\\launch.py',
  ])
})

test('with no active mod, workbench opens bare and the mod buttons only toast', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, { toasts, files: { 'C:\\proj\\skills\\dayz-preflight\\preflight.py': '' } })
  const ui = await openPane($)
  await ui.press({ key: 'workbench' })
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\skills\\dayz-launch-workbench\\launch.py'])
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
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\skills\\dayz-build-pbo\\build.py MyVest'])
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
    'python C:\\Users\\me\\.claude\\plugins\\cache\\dayz-n-chill\\agentic-z\\1.10.0\\skills\\dayz-build-pbo\\build.py MyVest',
  ])
})

test('a session started in a subfolder of the clone finds the clone and its active mod', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs, { cacheDirs: ['1.10.0'] })
  await $.session.start({ cwd: 'C:\\proj\\workspace\\MyVest', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Active mod: MyVest/ }))?.text).toBe('Active mod: MyVest')
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\skills\\dayz-build-pbo\\build.py MyVest'])
})

test('a press reads the active mod afresh, so /dayz-init after the pane opened needs no Refresh', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  const files: Record<string, string> = {
    'C:\\proj\\skills\\dayz-preflight\\preflight.py': '',
    'P:\\': '',
  }
  engineWith(on, runs, { toasts, files })
  const ui = await openPane($)
  expect((await ui.find({ type: 'Text', text: /Active mod:/ }))?.text).toBe('Active mod: none (run /dayz-init)')
  files['C:\\proj\\.claude\\local-memory\\dayz-init-state.json'] = '{"last_intent": {"mod_name": "MyVest"}}'
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(toasts).not.toContain('No active mod yet. Run /dayz-init first.')
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\skills\\dayz-build-pbo\\build.py MyVest'])
})

test('without a clone, a session in a subfolder finds the project state file above it', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs, {
    cacheDirs: ['1.10.0'],
    files: {
      'C:\\Users\\me\\.claude\\plugins\\cache\\dayz-n-chill\\agentic-z': '',
      'C:\\proj\\.claude\\local-memory\\dayz-init-state.json': '{"last_intent": {"mod_name": "MyVest"}}',
    },
  })
  await $.session.start({ cwd: 'C:\\proj\\workspace\\MyVest', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Active mod:/ }))?.text).toBe('Active mod: MyVest')
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([
    'python C:\\Users\\me\\.claude\\plugins\\cache\\dayz-n-chill\\agentic-z\\1.10.0\\skills\\dayz-build-pbo\\build.py MyVest',
  ])
})

test('without a clone, a state file in the home folder is not the active mod', async ($, on) => {
  // The A grade's defect: the walk reached ~\.claude, which state.py skips, so the
  // pane showed a mod every script then refused with "No project cached".
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, {
    toasts,
    cacheDirs: ['1.10.0'],
    files: {
      'C:\\Users\\me\\.claude\\plugins\\cache\\dayz-n-chill\\agentic-z': '',
      'C:\\Users\\me\\.claude\\local-memory\\dayz-init-state.json': '{"last_intent": {"mod_name": "MyVest"}}',
    },
  })
  await $.session.start({ cwd: 'C:\\Users\\me\\proj', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /Active mod:/ }))?.text).toBe('Active mod: none (run /dayz-init)')
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual([])
  expect(toasts).toContain('No active mod yet. Run /dayz-init first.')
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

test('a failing run toasts failed and keeps its [FAIL] line in the pane', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, {
    toasts,
    result: argv =>
      argv.some(a => a.endsWith('build.py'))
        ? { exitCode: 1, stdout: '[FAIL] lint: 2 errors\nmore', stderr: '' }
        : undefined,
  })
  const ui = await openPane($)
  await ui.press({ key: 'build' })
  expect(toasts).toEqual(['build: failed'])
  expect((await ui.find({ type: 'Text', text: /Last:/ }))?.text).toContain('Last: build failed [FAIL] lint: 2 errors')
  await ui.unmount()
})

test('an ask ERROR keeps its reason line in the pane', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, {
    toasts,
    result: argv =>
      argv.some(a => a.endsWith('ask.py'))
        ? { exitCode: 2, stdout: "ERROR\n  P:\\ is not mounted, so vanilla files can't be read. Run /dayz-workdrive.\n", stderr: '' }
        : undefined,
  })
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does food spoil' })
  expect(toasts).toEqual(['ask: failed'])
  const last = (await ui.find({ type: 'Text', text: /Last:/ }))?.text
  expect(last).toContain('Last: ask failed ERROR')
  expect(last).toContain('P:\\ is not mounted')
  await ui.unmount()
})

test('an ask with evidence shows the model answer as markdown', async ($, on) => {
  const runs: string[][] = []
  const prompts: string[] = []
  engineWith(on, runs, {
    result: argv =>
      argv.some(a => a.endsWith('ask.py'))
        ? { exitCode: 0, stdout: 'EVIDENCE 1 citation(s) via rag\n[1] P:\\scripts\\bleed.c:1-3  verified\n', stderr: '' }
        : undefined,
  })
  on('model.complete', (_: unknown, e: any) => {
    prompts.push(e.prompt)
    return { value: { isAnswered: true, text: 'Bleeding drains blood each tick [1].', usage: {} } }
  })
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  expect(prompts[0]).toContain('how does bleeding work')
  expect(prompts[0]).toContain('P:\\scripts\\bleed.c:1-3')
  expect((await ui.find({ type: 'Markdown' }))?.text).toBe('Bleeding drains blood each tick [1].')
  await ui.unmount()
})

test('Deep dive asks again with more and longer citations and a longer answer', async ($, on) => {
  const runs: string[][] = []
  const calls: any[] = []
  engineWith(on, runs, {
    result: argv =>
      argv.some(a => a.endsWith('ask.py'))
        ? { exitCode: 0, stdout: 'EVIDENCE 1 citation(s) via rag\n[1] P:\\scripts\\bleed.c:1-3  verified\n', stderr: '' }
        : undefined,
  })
  on('model.complete', (_: unknown, e: any) => {
    calls.push(e)
    return { value: { isAnswered: true, text: `Answer ${calls.length} [1].`, usage: {} } }
  })
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  await ui.press({ key: 'deepdive' })
  const asked = runs.filter(argv => argv.some(a => a.endsWith('ask.py'))).map(argv => argv.slice(2).join(' '))
  expect(asked).toEqual([
    '--top-k 10 --excerpt-lines 60 how does bleeding work',
    '--top-k 25 --excerpt-lines 200 how does bleeding work',
  ])
  expect(calls[0].system).toContain('under 400 words')
  expect(calls[1].system).toContain('under 900 words')
  expect(calls[1].maxTokens).toBeGreaterThan(calls[0].maxTokens)
  expect((await ui.find({ type: 'Markdown' }))?.text).toBe('Answer 2 [1].')
  // A deep dive is already the long answer: no second Deep dive button.
  expect(await ui.find({ key: 'deepdive' })).toBeFalsy()
  await ui.unmount()
})

// A store the test can seed and read back, as $.store keeps picks across sessions.
function storeIn(on: any, store: Record<string, unknown>) {
  on('store.get', (_: unknown, e: any) => ({ value: store[e.key] }))
  on('store.set', (_: unknown, e: any) => {
    store[e.key] = e.value
    return { value: undefined }
  })
}

const askEvidence = (argv: string[]) =>
  argv.some(a => a.endsWith('ask.py'))
    ? { exitCode: 0, stdout: 'EVIDENCE 1 citation(s) via rag\n[1] P:\\scripts\\bleed.c:1-3  verified\n', stderr: '' }
    : undefined

test('the ask pickers set sources, excerpt length and answer length, and are kept for the next session', async ($, on) => {
  const runs: string[][] = []
  const calls: any[] = []
  const store: Record<string, unknown> = {}
  engineWith(on, runs, { result: askEvidence })
  storeIn(on, store)
  on('model.complete', (_: unknown, e: any) => {
    calls.push(e)
    return { value: { isAnswered: true, text: 'Answer [1].', usage: {} } }
  })
  const ui = await openPane($)
  await ui.select({ key: 'ask-topk', value: '20' })
  await ui.select({ key: 'ask-lines', value: '150' })
  await ui.select({ key: 'ask-words', value: '900' })
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  await ui.unmount()
  const asked = runs.filter(argv => argv.some(a => a.endsWith('ask.py'))).map(argv => argv.slice(2).join(' '))
  expect(asked).toEqual(['--top-k 20 --excerpt-lines 150 how does bleeding work'])
  expect(calls[0].system).toContain('under 900 words')
  expect(store.askSettings).toEqual({ topK: '20', excerptLines: '150', words: '900' })

  // A new session starts from the stored picks.
  const again = await openPane($)
  await again.input({ key: 'ask', text: 'how does bleeding work' })
  await again.unmount()
  expect(runs.filter(argv => argv.some(a => a.endsWith('ask.py'))).map(argv => argv.slice(2, 6).join(' '))[1]).toBe(
    '--top-k 20 --excerpt-lines 150',
  )
})

test('a stored pick off the list goes back to its default, so the limits hold', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs, { result: askEvidence })
  storeIn(on, { askSettings: { topK: '500', excerptLines: '100', words: '99999' } })
  on('model.complete', (_: unknown, e: any) => {
    expect(e.system).toContain('under 400 words')
    return { value: { isAnswered: true, text: 'Answer [1].', usage: {} } }
  })
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  await ui.unmount()
  const asked = runs.filter(argv => argv.some(a => a.endsWith('ask.py'))).map(argv => argv.slice(2).join(' '))
  expect(asked).toEqual(['--top-k 10 --excerpt-lines 100 how does bleeding work'])
})

test('Continue in chat puts the question and answer in the prompt box without sending', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  const filled: string[] = []
  engineWith(on, runs, {
    toasts,
    result: argv =>
      argv.some(a => a.endsWith('ask.py'))
        ? { exitCode: 0, stdout: 'EVIDENCE 1 citation(s) via rag\n[1] P:\\scripts\\bleed.c:1-3  verified\n', stderr: '' }
        : undefined,
  })
  on('model.complete', () => ({ value: { isAnswered: true, text: 'Bleeding drains blood [1].', usage: {} } }))
  on('prompt.fill', (_: unknown, e: any) => {
    filled.push(e.text)
    return { isFilled: true, text: e.text }
  })
  on('prompt.submit', () => {
    throw new Error('Continue in chat must not send the prompt')
  })
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  await ui.press({ key: 'continue' })
  expect(filled.length).toBe(1)
  expect(filled[0]).toContain('how does bleeding work')
  expect(filled[0]).toContain('Bleeding drains blood [1].')
  expect(toasts).toContain('Added to the prompt box: add your follow-up and press Enter.')
  await ui.unmount()
})

test('an ask whose model call fails still shows the citations', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs, {
    result: argv =>
      argv.some(a => a.endsWith('ask.py'))
        ? { exitCode: 0, stdout: 'EVIDENCE 1 citation(s) via rag\n[1] P:\\scripts\\bleed.c:1-3  verified\n', stderr: '' }
        : undefined,
  })
  on('model.complete', () => ({ value: { isAnswered: false, reason: 'empty-reply', usage: {} } }))
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  expect(await ui.find({ type: 'Markdown' })).toBeFalsy()
  expect((await ui.find({ type: 'Text', text: /Last:/ }))?.text).toContain('[1] P:\\scripts\\bleed.c:1-3')
  await ui.unmount()
})

test('an ask that finds nothing says so instead of failed', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, {
    toasts,
    result: argv =>
      argv.some(a => a.endsWith('ask.py'))
        ? { exitCode: 1, stdout: 'NONE\n  note: no vanilla file matched the question\n', stderr: '' }
        : undefined,
  })
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how do unicorns fly' })
  expect(toasts).toEqual(['ask: nothing found'])
  const last = (await ui.find({ type: 'Text', text: /Last:/ }))?.text
  expect(last).toContain('Last: ask nothing found NONE')
  expect(last).toContain('note: no vanilla file matched')
  await ui.unmount()
})

test('a failing tasklist call does not stop a press', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  engineWith(on, runs, {
    toasts,
    hold: argv => (argv[0] === 'tasklist' ? Promise.reject(new Error('tasklist missing')) : undefined),
  })
  const ui = await openPane($)
  expect((await ui.find({ type: 'Text', text: /Test session/ }))?.text).toBe('Test session: stopped')
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(toasts).toEqual(['build: done'])
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\skills\\dayz-build-pbo\\build.py MyVest'])
})

test('a failing status check toasts, runs nothing and frees the lock', async ($, on) => {
  const runs: string[][] = []
  const toasts: string[] = []
  let broken = false
  engineWith(on, runs, { toasts, clockFails: () => broken })
  const ui = await openPane($)
  broken = true
  await ui.press({ key: 'build' })
  expect(scriptRuns(runs)).toEqual([])
  expect(toasts.length).toBe(1)
  expect(toasts[0]).toContain('build: failed (status check')
  broken = false
  await ui.press({ key: 'build' })
  await ui.unmount()
  expect(scriptRuns(runs)).toEqual(['python C:\\proj\\skills\\dayz-build-pbo\\build.py MyVest'])
  expect(toasts[1]).toBe('build: done')
})

test('a status check that fails at session start is not an unhandled rejection', async ($, on) => {
  const runs: string[][] = []
  engineWith(on, runs, { clockFails: () => true })
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
})

async function startWithMarketplace($: any, on: any, listed: string) {
  engine(on, [], listed)
  await $.session.start({ cwd: 'C:\\proj', surface: 'terminal', isInteractive: true })
  return $.command.run({ command: 'dayz-panel', args: '' })
}

test('a newer panel in the marketplace shows how to update', async ($, on) => {
  const reply = await startWithMarketplace($, on, '0.10.0')
  expect(reply.text).toContain('0.10.0 is out: run claude plugin update agentic-z-panel@dayz-n-chill')
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /Panel 0\.10\.0 is out/ })).toBeTruthy()
  await ui.unmount()
})

test('the same version in the marketplace shows no update notice', async ($, on) => {
  const reply = await startWithMarketplace($, on, '0.4.0')
  expect(reply.text).not.toContain('is out')
})

test('the start card checks setup, adds a server, and creates or imports a mod', async ($, on) => {
  const runs: string[][] = []
  engine(on, runs)
  await $.session.start({ cwd: 'C:\\proj', surface: 'terminal', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'preflight' })
  await ui.press({ key: 'addserver' })
  await ui.input({ key: 'newmod', text: '   ' })
  await ui.input({ key: 'newmod', text: 'MyVest' })
  await ui.input({ key: 'newmod', text: 'MyCrate by Brian' })
  await ui.input({ key: 'importmod', text: 'D:\\mods\\OldVest' })
  await ui.unmount()
  const lines = runs.map(argv => argv.join(' ')).filter(l => l.startsWith('python C:'))
  expect(lines).toEqual([
    'python C:\\proj\\skills\\dayz-preflight\\preflight.py',
    'python C:\\proj\\skills\\dayz-add-server\\add_server.py chernarus',
    'python C:\\proj\\skills\\dayz-new-mod\\new_mod.py MyVest',
    'python C:\\proj\\skills\\dayz-new-mod\\new_mod.py MyCrate --author Brian',
    'python C:\\proj\\skills\\dayz-import-mod\\import_mod.py --source D:\\mods\\OldVest',
  ])
})

test('the button above the prompt closes the panel when it is open, and opens it when it is closed', async ($, on) => {
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  const opened: string[] = []
  const closed: string[] = []
  engine(on, [], '0.4.0', opened)
  on('ui.close', (_: unknown, e: any) => {
    closed.push(e.id)
    return { value: undefined }
  })
  // The pane list the engine would answer: up while there have been more opens than closes.
  on('ui.panes', () => ({
    value: opened.length > closed.length ? [{ id: 'agentic-z', plugin: 'agentic-z-panel', title: 'Agentic-Z' }] : [],
  }))
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  const band = await $.ui.mount({ plugin: 'agentic-z-panel', component: 'AbovePrompt', surface: 'desktop', props: { hasSurvey: false } } as any)
  // The session opened the pane: the first press closes it, the second opens it again.
  await band.press({ key: 'open-panel' })
  expect(closed).toEqual(['agentic-z'])
  await band.press({ key: 'open-panel' })
  await band.unmount()
  expect(opened).toEqual(['agentic-z', 'agentic-z'])
  expect(closed).toEqual(['agentic-z'])
})

test('the bands beneath the button still draw', async ($, on) => {
  // Stands for another mod's band, such as the status strip.
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>status strip</Text>
  })
  engine(on, [], '0.4.0', [])
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  const band = await $.ui.mount({ plugin: 'agentic-z-panel', component: 'AbovePrompt', surface: 'desktop', props: { hasSurvey: false } } as any)
  expect((await band.find({ type: 'Text', text: /status strip/ }))?.text).toBe('status strip')
  await band.unmount()
})

test('a new session opens the panel without /dayz-panel', async ($, on) => {
  const opened: string[] = []
  engine(on, [], '0.4.0', opened)
  await $.session.start({ cwd: 'C:\\proj', surface: 'desktop', isInteractive: true })
  expect(opened).toEqual(['agentic-z'])
})

test('a session folder that no longer exists runs the script from the Agentic-Z root', async ($, on) => {
  const cwds: Record<string, string> = {}
  engineWith(on, [], {
    files: {
      'C:\\proj\\skills\\dayz-preflight\\preflight.py': '',
      'C:\\proj\\workspace\\MyVest': '',
    },
    seen: e => {
      if (e.argv[0] === 'cmd') cwds[e.argv[2]] = e.init.cwd
    },
  })
  await $.session.start({ cwd: 'C:\\proj\\workspace\\Gone', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'stop' })
  await ui.unmount()
  expect(cwds['C:\\proj\\skills\\dayz-stop-test\\stop_test.bat']).toBe('C:\\proj')

  await $.session.start({ cwd: 'C:\\proj\\workspace\\MyVest', surface: 'desktop', isInteractive: true })
  await $.command.run({ command: 'dayz-panel', args: '' })
  const again = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await again.press({ key: 'stop' })
  await again.unmount()
  expect(cwds['C:\\proj\\skills\\dayz-stop-test\\stop_test.bat']).toBe('C:\\proj\\workspace\\MyVest')
})

test('Dismiss clears the last run card and the update notice', async ($, on) => {
  engine(on, [], '9.9.9')
  const ui = await openPane($)
  await ui.press({ key: 'stop' })
  expect(await ui.find({ type: 'Text', text: /Last:/ })).toBeTruthy()
  await ui.press({ key: 'dismiss-run' })
  expect(await ui.find({ type: 'Text', text: /Last:/ })).toBeFalsy()
  expect(await ui.find({ type: 'Text', text: /9.9.9 is out/ })).toBeTruthy()
  await ui.press({ key: 'dismiss-update' })
  expect(await ui.find({ type: 'Text', text: /9.9.9 is out/ })).toBeFalsy()
  await ui.unmount()
})

test('an answer opens on the Answer tab and a build afterwards does not wipe it', async ($, on) => {
  engineWith(on, [], { result: askEvidence })
  on('model.complete', () => ({ value: { isAnswered: true, text: 'Bleeding drains blood [1].', usage: {} } }))
  const ui = await openPane($)
  await ui.input({ key: 'ask', text: 'how does bleeding work' })
  expect((await ui.find({ type: 'Markdown' }))?.text).toBe('Bleeding drains blood [1].')
  expect(await ui.find({ key: 'build' })).toBeFalsy()
  await ui.press({ key: 'tab-panel' })
  await ui.press({ key: 'build' })
  expect((await ui.find({ type: 'Text', text: /Last:/ }))?.text).toContain('Last: build done')
  await ui.press({ key: 'tab-answer' })
  expect((await ui.find({ type: 'Markdown' }))?.text).toBe('Bleeding drains blood [1].')
  await ui.unmount()
})

// An environment the test can read back, as $.env.set changes the process's own.
function envIn(on: any, env: Record<string, string>) {
  on('env.get', (_: unknown, e: any) => ({ value: env[e.name] }))
  on('env.set', (_: unknown, e: any) => {
    if (e.value === undefined) delete env[e.name]
    else env[e.name] = e.value
    return { value: {} }
  })
}

test('the Keys tab saves a key to the store and environment, shows only its tail, and clears it', async ($, on) => {
  const store: Record<string, unknown> = {}
  const env: Record<string, string> = {}
  engineWith(on, [])
  storeIn(on, store)
  envIn(on, env)
  const ui = await openPane($)
  await ui.press({ key: 'tab-keys' })
  expect((await ui.find({ type: 'Text', text: /VOYAGE_API_KEY:/ }))?.text).toContain('not set')
  await ui.input({ key: 'key-VOYAGE_API_KEY', text: '  pa-secret-1234  ' })
  expect(store.apiKeys).toEqual({ VOYAGE_API_KEY: 'pa-secret-1234' })
  expect(env.VOYAGE_API_KEY).toBe('pa-secret-1234')
  const shown = (await ui.find({ type: 'Text', text: /VOYAGE_API_KEY:/ }))?.text
  expect(shown).toContain('set here (…1234)')
  expect(shown).not.toContain('pa-secret')
  await ui.press({ key: 'clear-VOYAGE_API_KEY' })
  expect(store.apiKeys).toEqual({})
  expect(env.VOYAGE_API_KEY).toBeUndefined()
  await ui.unmount()
})

test('a saved key goes back into the environment when a new session starts', async ($, on) => {
  engineWith(on, [])
  const env: Record<string, string> = {}
  storeIn(on, { apiKeys: { TYPESAFE_API_KEY: 'ts-abcd' } })
  envIn(on, env)
  const ui = await openPane($)
  expect(env.TYPESAFE_API_KEY).toBe('ts-abcd')
  await ui.press({ key: 'tab-keys' })
  expect((await ui.find({ type: 'Text', text: /TYPESAFE_API_KEY:/ }))?.text).toContain('set here (…abcd)')
  await ui.unmount()
})
