# Agentic-Z Wiki

React + MUI wiki for the Agentic-Z website. Content comes from `src/content/guide.md` and `src/content/team.md`; each `## ` heading becomes a page, and the sidebar groups are set in `src/content.js`.

```
npm install
npm run dev       # local dev server
npm run build     # static site in dist/
```

- Logo: placeholder in `src/components/Logo.jsx`. Drop the real file in `src/assets/` and render it there.
- Colors and fonts: `src/theme.js` (`brand` and `fonts`).
- Diagrams: the docs point to `images/*.svg`; those are redrawn as MUI components. Specs live in `src/diagrams.js`, keyed by the image file name.
- The old Docusaurus wiki is in `archive/wiki-docusaurus/`. `/docs-sync` still targets the old `wiki/docs/` layout and will be rebuilt for this wiki.
