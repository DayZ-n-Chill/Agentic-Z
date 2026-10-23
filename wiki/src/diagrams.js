// Redrawn diagrams, keyed by the image file the source docs point to.
// Every label comes from the text around that image in the Guide or Agent Team doc.

const teamStructure = {
  type: 'tiers',
  tiers: [
    { label: 'You', detail: 'Describe the mod and approve the plan' },
    { label: 'Planning', items: ['dayz-orchestrator', 'dayz-mod-architect'] },
    { label: 'Team leads', items: ['Script', 'Config', 'Art', 'UI', 'Server', 'Release'] },
    { label: 'Workers', detail: 'One specialist per task' },
    { label: 'Gatekeepers', items: ['dayz-mod-reviewer', 'dayz-layout-validator', '/dayz-gate'] },
    { label: 'Playbook and reference files', items: ['.claude/skills/_shared/'] },
  ],
};

const specialistsJoin = {
  type: 'groups',
  caption: 'New specialists join as workers under an existing lead. The team loop is unchanged.',
  groups: [
    { label: 'Script lead', items: ['dayz-persistence-specialist', 'dayz-ai-specialist'] },
    { label: 'Config lead', items: ['dayz-vehicle-specialist', 'dayz-weapon-specialist'] },
    { label: 'Art lead', items: ['dayz-wearables-specialist', 'dayz-animation-specialist'] },
    { label: 'Any lead', items: ['dayz-audio-fx-specialist', 'dayz-physics-specialist'] },
  ],
};

const specialistCycle = {
  type: 'flow',
  loop: 'Repeat until every item is A+',
  steps: [
    { label: 'Read vanilla', detail: 'Every fact checked against the files on P:' },
    { label: 'Write reference files', detail: 'In our own words, nothing copied' },
    { label: 'Build the specialist', detail: 'A worker under an existing lead' },
    { label: 'Answer tests', detail: 'Known questions, scored answers' },
    { label: 'Independent grading', detail: 'Fresh reviewers each round' },
  ],
};

const versions = {
  type: 'versions',
  versions: [
    { label: 'v1.6.0', note: 'Released', built: 51, top: 0, tests: '84 tests' },
    { label: 'v1.7.0', note: 'Agent team', built: 51, top: 20 },
    { label: 'v2.0.0', note: 'Final', built: 163, top: 163, tests: '2,884 tests' },
  ],
  total: 163,
};

export const diagrams = {
  'guide-01-1.svg': {
    type: 'flow',
    steps: [
      { label: 'You' },
      { label: 'Your AI tool', items: ['Claude Code', 'Codex CLI', 'Gemini CLI'] },
      { label: 'Agentic-Z', items: ['Rules', 'Agents', 'Skills', 'Search server'], accent: true },
      { label: 'Acts on', items: ['Mod folder', 'P: drive', 'DayZ Tools', 'The game'] },
    ],
  },
  'guide-01-2.svg': {
    type: 'flow',
    steps: [
      { label: 'Check what you need', detail: 'Windows, DayZ Tools, P:, Python' },
      { label: 'Install one way', items: ['Clone as a template', 'Claude Code plugin'], detail: 'Never both' },
      { label: 'Run /dayz-init', detail: 'The setup wizard', accent: true },
      { label: 'Status hub', detail: 'On every later run' },
    ],
  },
  'guide-01-3.svg': {
    type: 'flow',
    loop: 'Fix any problems and repeat',
    steps: [
      { label: 'Ask an agent', detail: '"Add a hidden selection for the camo"' },
      { label: '/dayz-build-pbo', detail: 'Pack the mod' },
      { label: '/dayz-launch-test', detail: 'Diag server and client' },
      { label: 'Check the logs', detail: 'Or hand them to dayz-mod-debugger' },
      { label: '/dayz-stop-test', detail: 'Close DayZ' },
    ],
  },
  'guide-01-4.svg': teamStructure,
  'team-01-1.svg': teamStructure,
  'guide-01-5.svg': {
    type: 'flow',
    steps: [
      { label: 'Workers', detail: 'One task each' },
      { label: 'Lead checks', items: ['Mod review', 'Layout check'] },
      { label: 'Build check', detail: '/dayz-gate build' },
      { label: 'In-game test', detail: '/dayz-gate ingame' },
      { label: 'Behavior test', detail: 'When the plan lists checks' },
      { label: 'Visual check', detail: 'Against stored baselines' },
      { label: 'You', detail: 'A tested build', accent: true },
    ],
  },
  'guide-01-6.svg': {
    type: 'flow',
    steps: [
      { label: 'Vanilla files on P:', items: ['Scripts', 'Configs', 'Layouts', 'Materials'] },
      { label: 'Search index', items: ['/dayz-search-index', '/dayz-search-download'] },
      { label: 'dayz-rag server', items: ['search_dayz_source', 'get_dayz_file', 'list_indexed_sources'], accent: true },
      { label: 'Agent opens the real file', detail: 'A hit is only a lead' },
      { label: 'Answer', detail: 'With path:line references' },
    ],
  },
  'guide-01-7.svg': {
    type: 'tiers',
    caption: 'When two tiers disagree, the more specific tier wins.',
    tiers: [
      { label: '1 · Repo rules', items: ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md'], detail: 'Every agent, every task' },
      { label: '2 · DayZ rules', items: ['dayz-conventions.md', 'Topic files'], detail: 'All DayZ work' },
      { label: '3 · Agents and reference files', items: ['30 agents', '44 skills', '_shared/'], detail: 'Only when the task needs them' },
    ],
  },
  'guide-01-8.svg': {
    type: 'flow',
    steps: [
      { label: 'Your request' },
      { label: 'Keyword rules', detail: 'Checked first' },
      { label: 'Haiku router', detail: 'dayz-router, low cost' },
      { label: 'The right handler', items: ['Skill', 'Specialist', 'Team'], accent: true },
    ],
  },
  'guide-02-1.svg': specialistsJoin,
  'team-06-1.svg': specialistsJoin,
  'guide-02-2.svg': specialistCycle,
  'team-06-2.svg': specialistCycle,
  'guide-05-1.svg': versions,
  'team-02-1.svg': versions,
};
