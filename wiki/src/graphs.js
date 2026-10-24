// Flow diagrams with branches and loop-backs, drawn by components/Graph.jsx.
// Coordinates are in viewBox units; every label comes from the wiki text around the diagram.

const col = (i) => 110 + i * 132; // six team columns, 120 wide with a 12 gap

const LEADS = [
  ['Script lead', 'Enforce Script', ['Script engineer', 'Workbench plugins', 'Saving data', 'AI']],
  ['Config lead', 'Configs and classes', ['Config engineer', 'Vehicles', 'Weapons']],
  ['Art lead', 'Models and textures', ['Object Builder', 'Textures', 'Wearables', 'Animation']],
  ['UI lead', 'Menus and HUD', ['UI engineer', 'Figma cleaner', 'Figma to layout']],
  ['Server lead', 'Economy and maps', ['Server admin', 'Map builder']],
  ['Release lead', 'Builds and tests', ['Build engineer', 'Docs writer']],
];

const GATES = [
  ['Mod review', 'DayZ conventions'],
  ['Layout check', 'Figma-to-DayZ rules'],
  ['Build check', 'PBO packs clean'],
  ['In-game test', 'Loads, logs clean'],
  ['Behavior test', 'Items spawn and work'],
];

export const teamStructure = {
  type: 'graph',
  alt: 'The mod team: you, planning, six team leads with their workers, the gatekeepers, the test server, your final yes and publishing.',
  width: 980,
  height: 840,
  minWidth: 760,
  lanes: [
    { y: 39, label: 'You' },
    { y: 116, label: 'Layer 1', sub: 'Plan' },
    { y: 216, label: 'Layer 2', sub: 'Team leads' },
    { y: 352, label: 'Layer 3', sub: 'Workers' },
    { y: 521, label: 'Layer 4', sub: 'Gatekeepers' },
    { y: 634, label: 'Ship' },
    { y: 724, label: 'You' },
  ],
  groups: [{ x: 100, y: 272, w: 800, h: 178 }],
  nodes: [
    { id: 'you1', x: 390, y: 10, w: 220, h: 50, label: 'You', detail: 'Approve the mod plan', accent: true },
    { id: 'playbook', x: 110, y: 95, w: 200, h: 50, label: 'Shared playbook', detail: 'DayZ rules and reference files' },
    { id: 'orch', x: 370, y: 95, w: 260, h: 50, label: 'Mod orchestrator', detail: 'Splits the mod into small tasks' },
    { id: 'arch', x: 690, y: 95, w: 200, h: 50, label: 'Mod architect', detail: 'Plans classes, files and assets' },
    ...LEADS.map(([label, detail], i) => ({ id: `lead${i}`, x: col(i), y: 195, w: 120, h: 50, label, detail })),
    ...LEADS.flatMap(([, , workers], i) =>
      workers.map((w, k) => ({ id: `w${i}-${k}`, x: col(i), y: 285 + k * 32, w: 120, h: 26, label: w, small: true }))
    ),
    ...GATES.map(([label, detail], j) => ({ id: `gate${j}`, x: 110 + j * 158, y: 500, w: 148, h: 50, label, detail })),
    { id: 'ship', x: 380, y: 605, w: 240, h: 50, label: 'PBO on a test server', detail: 'Packed by the release lead' },
    { id: 'you2', x: 390, y: 695, w: 220, h: 50, label: 'You', detail: 'Final yes', accent: true },
    { id: 'publish', x: 410, y: 785, w: 180, h: 40, label: 'You publish' },
  ],
  edges: [
    { from: 'you1', to: 'orch', fs: 'b', ts: 't' },
    { from: 'orch', to: 'playbook', fs: 'l', ts: 'r', soft: true, noArrow: true },
    { from: 'orch', to: 'arch', fs: 'r', ts: 'l', soft: true, noArrow: true },
    ...LEADS.map((_, i) => ({ from: 'orch', to: `lead${i}`, fs: 'b', ts: 't', via: [[500, 172], [col(i) + 60, 172]] })),
    ...LEADS.map((_, i) => ({ from: `lead${i}`, to: `w${i}-0`, fs: 'b', ts: 't' })),
    { pts: [[500, 450], [500, 500]], label: 'Each finished task, then each wave', lx: 510, ly: 479 },
    { pts: [[500, 550], [500, 605]], label: 'Passes every gate', lx: 510, ly: 582 },
    { from: 'ship', to: 'you2', fs: 'b', ts: 't' },
    { from: 'you2', to: 'publish', fs: 'b', ts: 't' },
    { pts: [[890, 525], [925, 525], [925, 361], [900, 361]], loop: true },
    { pts: [[390, 720], [94, 720], [94, 120], [110, 120]], soft: true },
  ],
  notes: [
    { x: 944, y: 525, text: 'Fails go back to the worker', rotate: -90, loop: true },
    { x: 960, y: 525, text: 'The debugger reads only new errors', rotate: -90, loop: true },
    { x: 500, y: 438, text: 'Physics and Audio/FX serve every lead. Every specialist searches the vanilla files first.', anchor: 'middle' },
    { x: 104, y: 698, text: 'Your corrections become' },
    { x: 104, y: 712, text: 'playbook rules, with your yes' },
  ],
};

const checkY = (i) => 20 + i * 72;
const CHECKS = [
  ['worker', 'Worker', 'Finishes one task'],
  ['lead', 'Lead checks', 'Mod review, layout check for .layout'],
  ['build', 'Build check', '/dayz-gate build: the PBO packs clean'],
  ['ingame', 'In-game test', '/dayz-gate ingame: clean logs'],
  ['behavior', 'Behavior test', 'When the plan lists behavior checks'],
  ['visual', 'Visual check', 'Screenshots against stored baselines'],
  ['you', 'You', 'A tested build'],
];

export const teamChecks = {
  type: 'graph',
  alt: 'Work passes the lead checks, the build check, the in-game test, the behavior test and the visual check before it reaches you. A failure goes to triage and back to the worker.',
  width: 880,
  height: 530,
  laneX: 210,
  lanes: [
    { y: 48, label: 'Worker' },
    { y: 120, label: 'Lead', sub: 'Every task' },
    { y: 264, label: 'Orchestrator', sub: 'Once per wave' },
    { y: 480, label: 'You' },
  ],
  nodes: [
    ...CHECKS.map(([id, label, detail], i) => ({ id, x: 230, y: checkY(i), w: 300, h: 50, label, detail, accent: id === 'you' })),
    { id: 'triage', x: 610, y: 215, w: 250, h: 70, label: 'Triage', detail: 'Known error: fix and owner named\nNew error: the debugger reads the logs' },
  ],
  edges: [
    ...CHECKS.slice(0, -1).map(([id], i) => ({ from: id, to: CHECKS[i + 1][0], fs: 'b', ts: 't' })),
    ...[1, 2, 3, 4, 5].map((i) => ({ pts: [[530, checkY(i) + 25], [570, checkY(i) + 25]], loop: true, noArrow: true })),
    { pts: [[570, checkY(1) + 25], [570, checkY(5) + 25]], loop: true, noArrow: true },
    { pts: [[570, 250], [610, 250]], loop: true },
    { pts: [[735, 215], [735, 45], [530, 45]], loop: true, label: 'Back to the worker with notes', lx: 545, ly: 37 },
  ],
  notes: [{ x: 578, y: 160, text: 'Fails', loop: true }],
};

export const install = {
  type: 'graph',
  alt: 'Check what you need, install the Claude Code plugin (recommended) or, optionally, clone as a template, never both, then run /dayz-init: a setup wizard the first time and a status hub after that.',
  width: 900,
  height: 250,
  nodes: [
    { id: 'need', x: 10, y: 90, w: 175, h: 70, label: 'Check what you need', detail: 'Windows, DayZ Tools,\nP: drive, Python' },
    { id: 'clone', x: 245, y: 174, w: 195, h: 56, label: 'Clone as a template', detail: 'Optional' },
    { id: 'plugin', x: 245, y: 20, w: 195, h: 56, label: 'Claude Code plugin', detail: 'Recommended', accent: true },
    { id: 'init', x: 500, y: 97, w: 160, h: 56, label: '/dayz-init', detail: 'The setup wizard', mono: true, accent: true },
    { id: 'first', x: 720, y: 14, w: 170, h: 70, label: 'First run', detail: 'New or imported mod,\nmap, build and launch' },
    { id: 'later', x: 720, y: 166, w: 170, h: 70, label: 'Every later run', detail: 'Status hub for\nyour active mod' },
  ],
  edges: [
    { from: 'need', to: 'clone' },
    { from: 'need', to: 'plugin' },
    { from: 'clone', to: 'init' },
    { from: 'plugin', to: 'init' },
    { from: 'init', to: 'first' },
    { from: 'init', to: 'later' },
  ],
  notes: [{ x: 342, y: 130, text: 'Pick one, never both', anchor: 'middle' }],
};

export const router = {
  type: 'graph',
  alt: 'A request goes to keyword rules first, then Jev when a TypeSafe key is set, then the Haiku router. Each stage can hand it to the right handler.',
  width: 900,
  height: 300,
  nodes: [
    { id: 'req', x: 10, y: 20, w: 150, h: 50, label: 'Your request', detail: 'Typed or pasted' },
    { id: 'kw', x: 230, y: 20, w: 210, h: 50, label: 'Keyword rules', detail: 'No model tokens' },
    { id: 'jev', x: 230, y: 125, w: 210, h: 50, label: 'Jev', detail: 'Only with a TypeSafe key' },
    { id: 'haiku', x: 230, y: 230, w: 210, h: 50, label: 'Haiku router', detail: 'dayz-router, low cost' },
    { id: 'handler', x: 650, y: 20, w: 220, h: 260, label: 'The right handler', detail: 'A skill, a specialist\nor the whole team', accent: true },
  ],
  edges: [
    { from: 'req', to: 'kw' },
    { from: 'kw', to: 'handler', to_: -105, label: 'Match', lx: 460, ly: 38 },
    { from: 'kw', to: 'jev', fs: 'b', ts: 't', label: 'No match', lx: 345, ly: 103 },
    { from: 'jev', to: 'handler', label: 'Match', lx: 460, ly: 143 },
    { from: 'jev', to: 'haiku', fs: 'b', ts: 't', label: 'No key or no match', lx: 345, ly: 208 },
    { from: 'haiku', to: 'handler', to_: 105, label: 'Picks one', lx: 460, ly: 248 },
  ],
};

export const ragSearch = {
  type: 'graph',
  alt: 'An exact name goes to Grep, a question by meaning goes to RAG search over the index of the vanilla files. Either way the agent opens the real file, and answers with path:line only when the file confirms it.',
  width: 960,
  height: 330,
  nodes: [
    { id: 'q', x: 10, y: 20, w: 160, h: 56, label: 'A question', detail: 'About vanilla DayZ' },
    { id: 'dec', x: 220, y: 20, w: 200, h: 56, label: 'Exact name known?', detail: 'A class or symbol' },
    { id: 'grep', x: 480, y: 20, w: 170, h: 56, label: 'Grep', detail: 'Exact match' },
    { id: 'rag', x: 480, y: 130, w: 170, h: 56, label: 'RAG search', detail: 'search_dayz_source' },
    { id: 'open', x: 710, y: 75, w: 180, h: 56, label: 'Open the real file', detail: 'get_dayz_file' },
    { id: 'ans', x: 710, y: 250, w: 180, h: 64, label: 'Answer', detail: 'With path:line\nreferences', accent: true },
    { id: 'p', x: 10, y: 236, w: 170, h: 64, label: 'Vanilla files on P:', detail: 'Scripts, configs,\nlayouts, materials' },
    { id: 'idx', x: 240, y: 240, w: 180, h: 56, label: 'Search index', detail: '/dayz-search-index' },
  ],
  edges: [
    { from: 'q', to: 'dec' },
    { from: 'dec', to: 'grep', label: 'Yes', lx: 436, ly: 40 },
    { from: 'dec', to: 'rag', fs: 'b', ts: 'l', via: [[320, 158]], label: 'No: search by meaning', lx: 330, ly: 112 },
    { from: 'grep', to: 'open', to_: -12 },
    { from: 'rag', to: 'open', to_: 12 },
    { from: 'open', to: 'ans', fs: 'b', ts: 't', fo: 30, to_: 30, label: 'The file confirms it', lx: 830, ly: 195 },
    { pts: [[740, 131], [740, 205], [600, 205], [600, 186]], loop: true, label: 'Only a lead: search again', lx: 606, ly: 223 },
    { from: 'p', to: 'idx' },
    { pts: [[420, 268], [540, 268], [540, 186]] },
  ],
};
