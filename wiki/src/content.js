import guideMd from './content/guide.md?raw';
import teamMd from './content/team.md?raw';

export function slugify(text) {
  return String(text)
    .toLowerCase()
    .replace(/`/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}

// Split a markdown doc into one page per "## " heading.
function splitDoc(md, source) {
  const lines = md.split('\n');
  const pages = [];
  let current = null;
  let inFence = false;
  for (const line of lines) {
    if (line.startsWith('```')) inFence = !inFence;
    if (!inFence && line.startsWith('## ')) {
      const title = line.slice(3).trim();
      current = { title, slug: slugify(title), source, body: [] };
      pages.push(current);
      continue;
    }
    if (current) current.body.push(line);
  }
  return pages
    .filter((p) => p.slug !== 'contents')
    .map((p) => {
      const body = p.body.join('\n').trim();
      const headings = [];
      let fence = false;
      for (const l of p.body) {
        if (l.startsWith('```')) fence = !fence;
        if (!fence && l.startsWith('### ')) {
          const t = l.slice(4).trim();
          headings.push({ title: t, slug: slugify(t) });
        }
      }
      const summary =
        body
          .split('\n\n')
          .map((s) => s.trim())
          .find((s) => s && !/^[#|!\-\d`]/.test(s)) || '';
      return { ...p, body, headings, summary: summary.replace(/[`*_]/g, '') };
    });
}

const guidePages = splitDoc(guideMd, 'guide');
const seen = new Set(guidePages.flatMap((p) => [p.slug, ...p.headings.map((h) => h.slug)]));
// The team doc repeats the grading chapters from the guide; keep only what's new.
const teamPages = splitDoc(teamMd, 'team').filter((p) => !seen.has(p.slug));

export const intro = guideMd
  .split('\n')
  .find((l) => l.startsWith('This guide explains')) || '';

const GROUPS = [
  {
    id: 'start',
    title: 'Getting started',
    slugs: ['what-agentic-z-is', 'before-you-start', 'install-and-first-setup', 'where-everything-lives', 'your-daily-loop'],
  },
  {
    id: 'team',
    title: 'Agents & the team',
    slugs: [
      'agents',
      'the-mod-team',
      'how-the-team-works',
      'growing-the-team-new-specialists',
      'what-agentic-z-gives-an-ai-agent',
    ],
  },
  {
    id: 'knowledge',
    title: 'Skills & knowledge',
    slugs: [
      'the-skills',
      'rag-search',
      'the-three-tiers-of-rules',
      'token-savers-and-workflows',
      'why-vanilla', 'community-mods-and-add-ons',
    ],
  },
  {
    id: 'quality',
    title: 'Quality & grading',
    slugs: ['how-the-grading-works'],
  },
  {
    id: 'help',
    title: 'Help',
    slugs: ['safety', 'faq', 'troubleshooting', 'getting-help-and-contributing'],
  },
];

// Project-tracking chapters from the team doc. They describe the build, not how to use it, so the wiki leaves them out.
const HIDDEN = new Set(['status-and-next-steps', 'open-items-and-decisions', 'what-changed-from-agentic-z-160']);

const all = [...guidePages, ...teamPages];
const bySlug = Object.fromEntries(all.map((p) => [p.slug, p]));
const used = new Set();

export const groups = GROUPS.map((g) => ({
  ...g,
  pages: g.slugs
    .map((s) => bySlug[s])
    .filter(Boolean)
    .map((p) => {
      used.add(p.slug);
      return { ...p, group: g.title };
    }),
}));
const leftovers = all.filter((p) => !used.has(p.slug) && !HIDDEN.has(p.slug));
if (leftovers.length) {
  groups.push({ id: 'more', title: 'More', pages: leftovers.map((p) => ({ ...p, group: 'More' })) });
}

export const pages = groups.flatMap((g) => g.pages);

// Map every heading slug to the page that holds it, so in-doc links resolve.
export const anchorIndex = {};
for (const p of pages) {
  anchorIndex[p.slug] = { page: p.slug };
  for (const h of p.headings) if (!anchorIndex[h.slug]) anchorIndex[h.slug] = { page: p.slug, anchor: h.slug };
}

export const searchIndex = pages.flatMap((p) => [
  { label: p.title, page: p.slug, group: p.group },
  ...p.headings.map((h) => ({ label: h.title, page: p.slug, anchor: h.slug, group: p.title })),
]);

// Skills table from the Agent Team doc; the "The skills" page renders it as cards.
import skillsTable from './content/skills-table.md?raw';
export const skillGroups = (() => {
  const out = [];
  for (const line of skillsTable.split('\n')) {
    const m = line.match(/^\| (.+?) \|\s*(.*?)\s*\|$/);
    if (!m || m[1] === 'Skill' || m[1].startsWith('---')) continue;
    const cat = m[1].match(/^\*\*(.+)\*\*$/);
    if (cat) out.push({ title: cat[1], skills: [] });
    else if (out.length) out[out.length - 1].skills.push({ name: m[1].replace(/`/g, ''), desc: m[2].replace(/`/g, '') });
  }
  return out;
})();

// Rows of the "What you need" table on Before you start.
import requirementsTable from './content/requirements-table.md?raw';
export const requirements = requirementsTable
  .split('\n')
  .map((l) => l.match(/^\| (.+?) \|\s*(.*?)\s*\|$/))
  .filter((m) => m && m[1] !== 'Requirement' && !m[1].startsWith('---'))
  .map((m) => ({ name: m[1], purpose: m[2] }));
