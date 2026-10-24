// Redrawn diagrams, keyed by the image file the source docs point to.
// Every label comes from the text around that image in the Guide or Agent Team doc.

import { install, ragSearch, router, teamChecks, teamStructure } from './graphs.js';

const specialistsJoin = {
  type: 'groups',
  caption: 'The lead each specialist works under.',
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
    { label: 'v1.0.0', note: 'Released', built: 52, top: 0, tests: '85 tests' },
    { label: 'v1.5.0', note: 'Agent team', built: 52, top: 20 },
    { label: 'v2.0.0', note: 'Final', built: 193, top: 193, tests: '5,009 tests' },
  ],
  total: 193,
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
  'guide-01-2.svg': install,
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
  'guide-01-5.svg': teamChecks,
  'guide-01-6.svg': ragSearch,
  'guide-01-7.svg': {
    type: 'tiers',
    caption: 'When two tiers disagree, the more specific tier wins.',
    tiers: [
      { label: '1 · Repo rules', items: ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md'], detail: 'Every agent, every task' },
      { label: '2 · DayZ rules', items: ['dayz-conventions.md', 'Topic files'], detail: 'All DayZ work' },
      { label: '3 · Agents and reference files', items: ['30 agents', '44 skills', '_shared/'], detail: 'Only when the task needs them' },
    ],
  },
  'guide-01-8.svg': router,
  'guide-02-1.svg': specialistsJoin,
  'team-06-1.svg': specialistsJoin,
  'guide-02-2.svg': specialistCycle,
  'team-06-2.svg': specialistCycle,
  'guide-05-1.svg': versions,
  'team-02-1.svg': versions,
};
