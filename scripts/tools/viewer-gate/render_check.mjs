// SMOKE TEST for generated Three.js viewers. NOT a parity gate.
//
// What a green result means: the page loaded, mounted a canvas with real pixels, drew
// geometry at some point, reported the three revision it actually imported, and produced
// no page/request/console errors. It does NOT mean the content matches the baseline.
// Comparing baseline/after screenshots is the strongest cheap check for that, and it is what
// the migration behind this file leaned on. It is NOT proof either. A calibration round said
// so with a concrete attack: keep the render and the visible positions intact and change the
// inverse conversion used when EXPORTING a memory point or a proxy - swap Y/Z on the way back
// from Three coordinates to DayZ. The screenshots come out identical and the exported value is
// wrong. In an alignment tool the product is the coordinates, not the image.
//
// That boundary is not modesty, it is measured. Three review rounds killed three proxies:
//   v1 counted draw calls   -> deleting the only mesh passed (the grid kept drawing).
//   v2 counted TRIANGLES    -> a helper sphere alone passed; a line-drawn domain FALSE-FAILed.
//   v3 counted post-settle  -> a legitimate one-shot viewer FALSE-FAILed, and a decoy
//      frames + three URLs      network request forged the version.
// Each fix replaced one proxy with a better proxy, and the screenshots are one more: a stronger
// and more expensive projection carrying its own unobserved complement - depth, semantic
// identity, hidden elements, hit targets, and numeric output. There is no undefeatable
// instrument, so the useful question is not which one proves the content. It is: what does
// the instrument I am using leave unobserved, and who looks there? For these viewers the blind
// spot is the exported number, and only a round-trip of the value - export, re-import, compare
// against the original - or real use downstream can vouch for it. Do not add a fourth counter,
// and do not treat the pictures as the end of the argument either.
//
// v4 (2026-09-02):
//   - VERSION IS NOW A FACT, not a proxy: viewer_core emits `window.__THREE_REVISION` from
//     the module it actually imported, and the gate reads that. A URL, a comment or a decoy
//     fetch cannot forge it. Fail-closed: no handshake + --expected-three => FAIL.
//     `threeUrlsSeen` stays as DIAGNOSTIC only.
//   - `everDrew` / `everTri` are CUMULATIVE. Binding them to the post-settle window rejected
//     legitimate one-shot viewers. (Fixing only `everDrew` left `drewTriangles` failing the
//     same way - the defect escaping through the adjacent check.)
//   - Known and accepted: a canvas that is sized but visually hidden passes, and a helper
//     that draws triangles satisfies --min-tri-draws. Both are content/visibility questions
//     and belong to the visual comparison.
//
// Usage:
//   node render_check.mjs <html|url> [--png out.png] [--expected-three 0.185.1]
//                                    [--min-draws N] [--min-tri-draws N]
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// No machine-absolute paths in this file (pack rule). Both dependencies are resolved from
// the environment, and a miss says exactly what to set instead of throwing a stack trace.
//   PUPPETEER_MODULE            path or specifier for the puppeteer ESM entry
//   PUPPETEER_EXECUTABLE_PATH   Chrome/Chromium binary (CHROME_PATH also accepted)
async function loadPuppeteer() {
  const tried = [];
  const candidates = [process.env.PUPPETEER_MODULE, 'puppeteer', 'puppeteer-core'].filter(Boolean);
  for (const c of candidates) {
    const spec = /^[a-z]+:/i.test(c) ? c : (fs.existsSync(c) ? pathToFileURL(path.resolve(c)).href : c);
    try { return (await import(spec)).default; } catch (e) { tried.push(`${c}: ${String(e).slice(0, 90)}`); }
  }
  console.error('Cannot load puppeteer. Set PUPPETEER_MODULE to its ESM entry, or install it.\nTried:\n  ' + tried.join('\n  '));
  process.exit(2);
}
function findChrome() {
  const fromEnv = process.env.PUPPETEER_EXECUTABLE_PATH || process.env.CHROME_PATH;
  if (fromEnv) return fromEnv;
  const guesses = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ];
  return guesses.find(g => fs.existsSync(g));   // undefined => puppeteer's bundled browser
}

const puppeteer = await loadPuppeteer();
const CHROME = findChrome();
const argv = process.argv.slice(2);
const target = argv[0];
const flag = (n, d) => { const i = argv.indexOf(n); return i > -1 ? argv[i + 1] : d; };
const pngOut = flag('--png', null);
const expectedThree = flag('--expected-three', null);
const minDraws = Number(flag('--min-draws', '1'));
// Optional HEURISTIC, off by default. When a viewer is known to draw triangles, this
// still catches 'the mesh is gone' (helpers draw LINES). It is defeatable - a helper
// that draws triangles satisfies it (R21b-01) - so it is a cheap extra net, never proof.
const minTriDraws = Number(flag('--min-tri-draws', '0'));
if (!target) {
  console.error('usage: render_check.mjs <html|url> [--png f] [--expected-three V] [--min-draws N]');
  process.exit(2);
}
// R21b-05: a bare relative path used to become file:///controls/x.html (cwd dropped).
const url = /^https?:\/\//.test(target) ? target : pathToFileURL(path.resolve(process.cwd(), target)).href;

const browser = await puppeteer.launch({
  headless: 'new',
  ...(CHROME ? { executablePath: CHROME } : {}),
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox']
});
const page = await browser.newPage();
const pageErrors = [], failedReq = [], consoleErrors = [], threeRequested = new Set();
page.on('pageerror', e => pageErrors.push(String(e).slice(0, 220)));
page.on('requestfailed', r => failedReq.push(r.url().slice(0, 160)));
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
// R21b-03: runtime evidence. Only a real fetch of a three build counts as "the version used".
page.on('request', r => {
  const m = r.url().match(/three@(\d+\.\d+\.\d+)\/build\/|three\.js\/(r\d+)\/build\//);
  if (m) threeRequested.add(m[1] || m[2]);
});

await page.evaluateOnNewDocument(() => {
  const TRI = [4, 5, 6], LINE = [1, 2, 3];
  window.__frame = { tri: 0, line: 0, point: 0, total: 0 };
  window.__frames = [];
  window.__everDrew = 0;   // cumulative, never reset: 'did it ever draw'
  window.__everTri  = 0;   // same, for triangle draws
  window.__resetFrames = () => { window.__frames = []; window.__frame = { tri: 0, line: 0, point: 0, total: 0 }; };
  const bump = mode => {
    const f = window.__frame; f.total++; window.__everDrew++;
    if (TRI.includes(mode)) window.__everTri++;
    if (TRI.includes(mode)) f.tri++; else if (LINE.includes(mode)) f.line++; else f.point++;
  };
  for (const ctor of [self.WebGLRenderingContext, self.WebGL2RenderingContext]) {
    if (!ctor) continue;
    for (const fn of ['drawElements', 'drawArrays', 'drawElementsInstanced', 'drawArraysInstanced']) {
      const orig = ctor.prototype[fn];
      if (orig) ctor.prototype[fn] = function (mode, ...rest) { bump(mode); return orig.call(this, mode, ...rest); };
    }
  }
  (function sample() {
    const f = window.__frame;
    if (f.total > 0) window.__frames.push(f);
    window.__frame = { tri: 0, line: 0, point: 0, total: 0 };
    requestAnimationFrame(sample);
  })();
});

let status = 'OK', canvas = null, canvasAtSettle = null, perFrame = null, framesSeen = 0, runtime = { revision: null, everDrew: 0, everTri: 0 };
try {
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.waitForFunction('window.__frames && window.__frames.length > 0', { timeout: 20000 }).catch(() => {});
  await page.evaluate(() => new Promise(r => setTimeout(r, 700)));            // settle (damping, async setup)
  // Canvas as the page actually loaded it. Measured BEFORE the resize nudge below: that
  // nudge fires the viewer's own resize handler, which repairs a 0x0 canvas and would
  // hide the defect (the nudge's fix for R21b-02 was masking R21b-04). A viewer that
  // shows nothing until the window is resized is broken for double-click use.
  canvasAtSettle = await page.evaluate(() => {
    const c = document.querySelector('canvas');
    return c ? { w: c.width, h: c.height } : null;
  });
  // R21b-02: throw away everything observed so far, then measure a FRESH window. The resize
  // nudge makes on-demand viewers redraw, so a one-shot viewer is still measurable here.
  await page.evaluate(() => { window.__resetFrames(); window.dispatchEvent(new Event('resize')); });
  await page.evaluate(() => new Promise(r => setTimeout(r, 700)));
  const s = await page.evaluate(() => {
    const fr = window.__frames || [];
    const max = k => fr.reduce((a, f) => Math.max(a, f[k]), 0);
    return { n: fr.length, tri: max('tri'), line: max('line'), point: max('point'), total: max('total') };
  });
  framesSeen = s.n;
  perFrame = { totalDraws: s.total, triangleDraws: s.tri, lineDraws: s.line, pointDraws: s.point };
  canvas = await page.evaluate(() => {
    const c = document.querySelector('canvas');
    return c ? { w: c.width, h: c.height } : null;
  });
  runtime = await page.evaluate(() => ({
    revision: (typeof window.__THREE_REVISION !== 'undefined') ? String(window.__THREE_REVISION) : null,
    everDrew: window.__everDrew || 0,
    everTri: window.__everTri || 0
  }));
  if (pngOut) await page.screenshot({ path: pngOut });
} catch (e) { status = 'LOAD_FAIL: ' + String(e).slice(0, 160); }

const threeLoaded = [...threeRequested];
const checks = {
  loaded:          status === 'OK',
  noPageErrors:    pageErrors.length === 0,
  noFailedReq:     failedReq.length === 0,
  noConsoleErr:    consoleErrors.length === 0,
  canvasHasPixels: !!canvas && canvas.w > 0 && canvas.h > 0
                     && !!canvasAtSettle && canvasAtSettle.w > 0 && canvasAtSettle.h > 0,  // R21b-04
  everDrew:        runtime.everDrew >= minDraws,
  // Same fix as everDrew: a one-shot viewer draws nothing AFTER settle, so binding this
  // to the post-settle window rejected legitimate viewers - the defect escaping sideways.
  drewTriangles:   minTriDraws <= 0 ? true : (runtime.everTri >= minTriDraws),
  versionOk:       expectedThree === null
                     ? true
                     : runtime.revision !== null && runtime.revision === expectedThree.split('.')[1]
};
const pass = Object.values(checks).every(Boolean);

console.log(JSON.stringify({
  file: target, resolved: url, pass, status, checks,
  failedChecks: Object.entries(checks).filter(([, v]) => !v).map(([k]) => k),
  threeRevisionReported: runtime.revision, expectedThree, minTriDraws,
  everDrewTotal: runtime.everDrew, everTriTotal: runtime.everTri,
  threeUrlsSeen: threeLoaded,   // DIAGNOSTIC ONLY - a decoy fetch can forge this
  framesSampledAfterSettle: framesSeen,
  perFrame,           // TELEMETRY ONLY - not evidence about content. See header.
  canvas, canvasAtSettle, pageErrors, failedRequests: failedReq, consoleErrors,
  note: 'SMOKE TEST. Green does NOT mean parity with the baseline; parity is visual comparison.'
}, null, 2));
await browser.close();
process.exit(pass ? 0 : 1);
