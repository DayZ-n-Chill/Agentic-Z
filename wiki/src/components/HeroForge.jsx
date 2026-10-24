import { useEffect, useRef } from 'react';
import { useTheme } from '@mui/material/styles';
import { fonts } from '../theme.js';
import { MODELS } from './forgeModels.js';

// The right side of the home card: a small crew of agents builds DayZ objects as 3D wireframes,
// a few edges at a time, from the ground up. Each finished object holds, dissolves, and the next
// one starts. Drag to turn the model; it goes back to a slow spin a moment after you let go.
// The models are hand-modelled in code (forgeModels.js), not game assets. Edges on the far side
// of a model are drawn faintly. Hidden on narrow screens, where the text takes the full card width.

// Lines of code each agent "writes" as it works, typed out beside it.
const CODE = [
  'modded class ItemBase',
  'override void EEInit()',
  'super.EEInit();',
  'class CfgVehicles {',
  'scope = 2;',
  'weight = 1250;',
  'inventorySlot[] = {"Back"};',
  'hiddenSelections[] = {"camo"};',
  'class Geometry : LOD {',
  'rvmat = "mat_01.rvmat";',
  'ref array<EntityAI> m_Parts;',
  'SetHealth("", "", 100);',
  'GetGame().CreateObject(t, pos);',
  'proxy: attachment_back',
  'return true;',
  '};',
];

const CREW = 5;
const HOLD = 3.2;
const FADE = 1.6;
const ARRIVE = 1.8; // seconds for the crew to glide into place before a build
const BUILD = 11; // seconds to build one model, whatever its edge count
const GLYPH = 2.2; // seconds a typed line of code stays up
const LOOK = 24; // each agent takes the nearest unbuilt edge among the next few in build order
const REZ = 1.6; // seconds for a finished wireframe to fill in as the solid model
const SHOWN = 4.5; // seconds the solid model stays up

// The solid model, drawn with WebGL under the wireframe: the same turn and perspective as the
// 2D projection, simple light from the upper left, and a rez line sweeping up that cuts the
// model off and glows where it is filling in.
const VS = `
attribute vec3 aPos; attribute vec3 aNrm; attribute vec3 aCol;
uniform vec4 uView; uniform vec2 uScale;
varying vec3 vCol; varying float vY; varying float vLight;
void main() {
  float cy = uView.x, sy = uView.y, cp = uView.z, sp = uView.w;
  vec3 p = aPos;
  float x = p.x * cy - p.z * sy; float z1 = p.x * sy + p.z * cy;
  float y = p.y * cp - z1 * sp; float z = p.y * sp + z1 * cp;
  vec3 n = aNrm;
  float nx = n.x * cy - n.z * sy; float nz1 = n.x * sy + n.z * cy;
  vec3 vn = normalize(vec3(nx, n.y * cp - nz1 * sp, n.y * sp + nz1 * cp));
  vLight = 0.32 + 0.68 * max(0.0, dot(vn, normalize(vec3(-0.35, 0.55, -1.0))));
  float k = 3.4 / (3.4 + z);
  gl_Position = vec4(x * k * uScale.x, y * k * uScale.y, z * 0.3, 1.0);
  vCol = aCol; vY = p.y;
}`;
const FS = `
precision mediump float;
uniform float uReveal; uniform float uAlpha; uniform vec3 uGlow; uniform vec3 uCore;
varying vec3 vCol; varying float vY; varying float vLight;
void main() {
  float d = uReveal - vY;
  if (d < 0.0) discard;
  vec3 c = vCol * vLight;
  // Scan lines over the fresh part, and a hot band at the rez line.
  float band = 1.0 - smoothstep(0.0, 0.09, d);
  c = mix(c, uGlow, band * 0.85);
  c = mix(c, uCore, (1.0 - smoothstep(0.0, 0.015, d)));
  c *= 0.93 + 0.07 * step(0.5, fract(gl_FragCoord.y / 3.0));
  gl_FragColor = vec4(c * uAlpha, uAlpha);
}`;

export default function HeroForge() {
  const ref = useRef(null);
  const glRef = useRef(null);
  const theme = useTheme();
  const dark = theme.palette.mode === 'dark';
  const accent = theme.palette.primary.main;
  // The white-hot centre of fresh lines and beam tips.
  const core = dark ? '#FFF1D6' : '#C27A12';
  // Lasers and sparks run a little redder than the wire, like the printer beams in Tron: Ares.
  const laser = dark ? '#FF5A1F' : '#D2490F';

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas && canvas.getContext('2d');
    if (!ctx) return undefined;

    // A soft round puff of accent-coloured light, drawn many times for the smoke.
    const puff = document.createElement('canvas');
    puff.width = 64;
    puff.height = 64;
    {
      const pc = puff.getContext('2d');
      const g = pc.createRadialGradient(32, 32, 0, 32, 32, 32);
      const hex = accent.replace('#', '');
      const rgb = [0, 2, 4].map((i) => parseInt(hex.length === 3 ? hex[i / 2] + hex[i / 2] : hex.slice(i, i + 2), 16));
      g.addColorStop(0, `rgba(${rgb},1)`);
      g.addColorStop(0.4, `rgba(${rgb},0.45)`);
      g.addColorStop(1, `rgba(${rgb},0)`);
      pc.fillStyle = g;
      pc.fillRect(0, 0, 64, 64);
    }

    // WebGL for the solid model, if the browser has it; without it the forge stays wireframe.
    const glc = glRef.current;
    const gl = glc && glc.getContext('webgl', { premultipliedAlpha: true, antialias: true });
    let prog = null;
    if (gl) {
      const sh = (type, src) => {
        const o = gl.createShader(type);
        gl.shaderSource(o, src);
        gl.compileShader(o);
        return o;
      };
      prog = gl.createProgram();
      gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS));
      gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) prog = null;
      if (prog) gl.getExtension('OES_element_index_uint');
    }
    const rgbOf = (hex) => {
      const h = hex.replace('#', '');
      return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
    };
    const b64 = (str) => {
      const bin = atob(str);
      const out = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
      return out.buffer;
    };
    // Upload a model's solid mesh once: positions and normals are packed integers, colours bytes.
    const solid = (M) => {
      if (!prog || !M.render) return null;
      if (!M.gl) {
        const R = M.render;
        const buf = (data, target = gl.ARRAY_BUFFER) => {
          const b = gl.createBuffer();
          gl.bindBuffer(target, b);
          gl.bufferData(target, data, gl.STATIC_DRAW);
          return b;
        };
        const pos = new Int16Array(b64(R.pos));
        const f = new Float32Array(pos.length);
        for (let i = 0; i < pos.length; i++) f[i] = pos[i] / 32767;
        const idx = R.i32 ? new Uint32Array(b64(R.idx)) : new Uint16Array(b64(R.idx));
        M.gl = {
          pos: buf(f),
          nrm: buf(new Int8Array(b64(R.nrm))),
          col: buf(new Uint8Array(b64(R.col))),
          idx: buf(idx, gl.ELEMENT_ARRAY_BUFFER),
          count: idx.length,
          type: R.i32 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT,
        };
      }
      return M.gl;
    };

    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let W = 0;
    let H = 0;
    const resize = () => {
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      for (const c of [canvas, glc]) {
        if (c && (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr))) {
          c.width = Math.round(W * dpr);
          c.height = Math.round(H * dpr);
        }
      }
    };

    // View: yaw spins slowly on its own; dragging sets yaw and pitch directly.
    const view = { yaw: 0.6, pitch: -0.32, vy: 0, dragging: false, lastX: 0, lastY: 0, idle: 0 };
    const onDown = (ev) => {
      view.dragging = true;
      view.lastX = ev.clientX;
      view.lastY = ev.clientY;
      view.vy = 0;
      canvas.setPointerCapture(ev.pointerId);
      canvas.style.cursor = 'grabbing';
    };
    const onMove = (ev) => {
      if (!view.dragging) return;
      const dx = ev.clientX - view.lastX;
      const dy = ev.clientY - view.lastY;
      view.lastX = ev.clientX;
      view.lastY = ev.clientY;
      view.yaw += dx * 0.01;
      view.pitch = Math.max(-1.3, Math.min(1.3, view.pitch + dy * 0.01));
      view.vy = dx * 0.01;
      view.idle = 0;
      if (still) draw(performance.now());
    };
    const onUp = (ev) => {
      view.dragging = false;
      canvas.style.cursor = 'grab';
      if (canvas.hasPointerCapture(ev.pointerId)) canvas.releasePointerCapture(ev.pointerId);
    };
    canvas.addEventListener('pointerdown', onDown);
    canvas.addEventListener('pointermove', onMove);
    canvas.addEventListener('pointerup', onUp);
    canvas.addEventListener('pointercancel', onUp);

    // Build state for the current model. Its edges are already in bottom-up order; `head` is the
    // first one not yet taken.
    let mi = 0;
    let built = null;
    let taken = null;
    let heads = [];
    let done = 0;
    let phase = 'build';
    let phaseT = 0;
    let glyphs = [];
    let wisps = [];
    let thoughts = [];
    let heat = null; // when each edge was finished, for the glow of fresh work
    let frontY = -1; // height of the build line, for the scan ring
    let shards = []; // little cubes of light that fly in and lock onto fresh work
    let sparks = []; // short streaks thrown off where a beam lands
    const crew = Array.from({ length: CREW }, (_, k) => ({ p: [Math.cos(k) * 1.6, 1.2, Math.sin(k) * 1.6], job: -1, from: null, t: 0, trail: [], nextLine: 0.3 * k, nextThought: 0, em: [Math.cos(k) * 1.6, 1.4, Math.sin(k) * 1.6] }));

    // A model's widest reach around its upright axis at each height, for the scan ring.
    const reach = (M, y) => {
      if (!M.reach) {
        M.reach = new Float32Array(24);
        for (const p of M.v) {
          const i = Math.max(0, Math.min(23, Math.floor(((p[1] + 1) / 2) * 24)));
          M.reach[i] = Math.max(M.reach[i], Math.hypot(p[0], p[2]));
        }
      }
      return M.reach[Math.max(0, Math.min(23, Math.floor(((y + 1) / 2) * 24)))];
    };

    // Split a model's edges into one slice per agent by angle around the model, so the crew
    // works on different sides at once. Each slice keeps the bottom-up order.
    const slices = (M) => {
      if (!M.slices) {
        const ang = M.e.map(({ a, b }) => Math.atan2(M.v[a][0] + M.v[b][0], M.v[a][2] + M.v[b][2]));
        const order = ang.map((_, k) => k).sort((p, q) => ang[p] - ang[q]);
        const of = new Uint8Array(M.e.length);
        order.forEach((k, i) => (of[k] = Math.floor((i * CREW) / order.length)));
        M.slices = Array.from({ length: CREW }, (_, g) => M.e.map((_, k) => k).filter((k) => of[k] === g));
      }
      return M.slices;
    };

    const startModel = () => {
      const M = MODELS[mi];
      built = new Float32Array(M.e.length);
      heat = new Float32Array(M.e.length).fill(-10);
      taken = new Uint8Array(M.e.length);
      heads = slices(M).map(() => 0);
      // Stagger the first typed lines so the crew doesn't all speak at once.
      const t0 = performance.now() / 1000;
      crew.forEach((c, k) => (c.nextLine = t0 + (still ? 0 : ARRIVE) + 0.5 + k * 0.45));
      done = 0;
      // The crew first glides over to its slices, then starts building.
      phase = still ? 'build' : 'arrive';
      phaseT = 0;
      crew.forEach((c) => (c.arr = null));
    };
    startModel();
    if (still) {
      built.fill(1);
      done = built.length;
    }

    const lerp = (a, b, t) => a + (b - a) * t;
    const lerp3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
    const norm2 = (p) => {
      const l = Math.hypot(p[0], p[2]) || 1;
      return [p[0] / l, p[2] / l];
    };
    const dist3 = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

    // The nearest free edge to `p` among the next LOOK of slice `g`. An agent whose slice is
    // finished helps with the slice that has the most left.
    const nextEdge = (M, p, g) => {
      const sl = slices(M);
      const left = (i) => sl[i].length - heads[i];
      for (let i = 0; i < sl.length; i++) while (heads[i] < sl[i].length && taken[sl[i][heads[i]]]) heads[i]++;
      if (left(g) === 0) g = sl.reduce((m, _, i) => (left(i) > left(m) ? i : m), 0);
      const list = sl[g];
      let best = -1;
      let bd = Infinity;
      for (let i = heads[g], seen = 0; i < list.length && seen < LOOK; i++) {
        const k = list[i];
        if (taken[k]) continue;
        seen++;
        const d = dist3(p, M.v[M.e[k].a]);
        if (d < bd) [best, bd] = [k, d];
      }
      return best;
    };

    const step = (dt, now) => {
      const M = MODELS[mi];
      if (!view.dragging) {
        view.idle += dt;
        // Coast after a drag, then settle back into the slow spin.
        view.vy *= Math.pow(0.04, dt);
        view.yaw += view.vy + (view.idle > 1.5 ? 0.18 * dt : 0);
      }
      phaseT += dt;
      // Each agent spends `per` seconds on an edge: hop to its start, then trace it.
      const per = (BUILD * CREW) / M.e.length;
      let ys = 0;
      let yn = 0;
      crew.forEach((c, ci) => {
        // The agent itself hovers above and outside the point it is working on, like a printer
        // head, and fires a beam down to it.
        const out = norm2(c.p);
        const target = phase === 'build' ? [c.p[0] + out[0] * 0.25, c.p[1] + 0.32, c.p[2] + out[1] * 0.25] : c.p;
        c.em = lerp3(c.em, target, Math.min(1, dt * 5));
        // Glides, but never trails so far behind that the beam gets long.
        const lag = dist3(c.em, target);
        if (lag > 0.45) c.em = lerp3(target, c.em, 0.45 / lag);
        if (phase === 'build' && c.job >= 0) {
          ys += c.p[1];
          yn++;
        }
        // A short trail of where the agent has been, and sparks shed where the beam lands.
        c.trail.push(c.em);
        if (c.trail.length > 16) c.trail.shift();
        if (!still && phase === 'build' && Math.random() < dt * 16) {
          wisps.push({ h: [c.p.slice()], born: now, life: 1.6 + Math.random() * 1.2, seed: Math.random() * 6.3, v: [(Math.random() - 0.5) * 0.08, 0.07 + Math.random() * 0.07, (Math.random() - 0.5) * 0.08] });
        }
        if (!still && phase === 'build' && c.job >= 0 && sparks.length < 160) {
          for (let n = Math.floor(dt * 30 + Math.random()); n > 0; n--) {
            const o = norm2(c.p);
            const sp = 0.4 + Math.random() * 0.6;
            const a = Math.random() * Math.PI * 2;
            sparks.push({ p: c.p.slice(), v: [o[0] * sp * 0.6 + Math.cos(a) * sp * 0.5, 0.3 + Math.random() * 0.7, o[1] * sp * 0.6 + Math.sin(a) * sp * 0.5], born: now, life: 0.35 + Math.random() * 0.4 });
          }
        }
        // Every so often, the agent types a line of code beside itself (one line at a time).
        if (phase === 'build' && now > c.nextLine) {
          c.nextLine = now + GLYPH + 0.4 + Math.random() * 1.6;
          glyphs.push({ c, text: CODE[Math.floor(Math.random() * CODE.length)], born: now });
        }
        // Between models the agents idle and "think": little blocks of code-like squares flicker
        // beside them, a few short rows like a line of code seen from far off.
        if ((phase === 'hold' || phase === 'fade') && now > c.nextThought) {
          c.nextThought = now + 0.3 + Math.random() * 0.5;
          const rows = 1 + Math.floor(Math.random() * 3);
          const cells = [];
          for (let r = 0; r < rows; r++) {
            const indent = Math.floor(Math.random() * 3);
            const len = 2 + Math.floor(Math.random() * 6);
            for (let k = 0; k < len; k++) if (Math.random() > 0.15) cells.push([indent + k, r]);
          }
          thoughts.push({ c, cells, born: now, dx: 7 + Math.random() * 6, dy: -6 - Math.random() * 10 });
        }
        if (phase === 'arrive') {
          // Glide round the model to where this agent's slice starts, on a curved path that eases
          // in and out and lifts a little on the way, instead of flying straight there.
          if (!c.arr) {
            const sl = slices(M)[ci];
            const dest = M.v[M.e[sl.length ? sl[0] : 0].a];
            const o = norm2(dest);
            const to = [dest[0] + o[0] * 0.25, dest[1] + 0.32, dest[2] + o[1] * 0.25];
            const cyl = (q) => [Math.atan2(q[0], q[2]), Math.hypot(q[0], q[2]), q[1]];
            const A = cyl(c.em);
            const B = cyl(to);
            let da = B[0] - A[0];
            da = ((da + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
            // Swing the long way round now and then, so they don't all take the short route.
            if (ci % 2) da += da > 0 ? -Math.PI * 2 * 0.25 : Math.PI * 2 * 0.25;
            c.arr = { A, da, B, dest, delay: ci * 0.12 };
          }
          const { A, da, B, dest, delay } = c.arr;
          const u = Math.max(0, Math.min(1, (phaseT - delay) / (ARRIVE - 0.5)));
          const e = u * u * u * (u * (u * 6 - 15) + 10); // smooth start and stop
          const ang = A[0] + da * e;
          const rad = lerp(A[1], B[1], e) + 0.25 * Math.sin(Math.PI * e);
          const y = lerp(A[2], B[2], e) + 0.2 * Math.sin(Math.PI * e);
          c.em = [Math.sin(ang) * rad, y, Math.cos(ang) * rad];
          c.p = dest;
          return;
        }
        if (phase !== 'build') {
          // Between models the crew swarms round the model like electrons round an atom: each
          // agent on its own tilted orbit and speed, with a little organic wobble.
          const tilt = 0.5 + 0.9 * ((ci * 0.618) % 1);
          const spin = (ci / CREW) * Math.PI * 2;
          const a = now * (0.7 + 0.25 * ci) * (ci % 2 ? -1 : 1) + ci * 2.1;
          const r = 1.1 + 0.12 * Math.sin(now * 1.3 + ci * 1.7);
          // A circle in the x/z plane, tipped over by `tilt`, then turned by `spin`.
          let o = [Math.cos(a) * r, 0, Math.sin(a) * r];
          o = [o[0], -o[2] * Math.sin(tilt), o[2] * Math.cos(tilt)];
          o = [o[0] * Math.cos(spin) + o[2] * Math.sin(spin), o[1], -o[0] * Math.sin(spin) + o[2] * Math.cos(spin)];
          const wob = 0.06;
          o = [o[0] + wob * Math.sin(now * 2.3 + ci), o[1] + wob * Math.sin(now * 1.9 + ci * 2), o[2] + wob * Math.cos(now * 2.1 + ci * 3)];
          c.p = lerp3(c.p, o, Math.min(1, dt * 2.5));
          return;
        }
        let left = dt;
        while (left > 0) {
          if (c.job < 0) {
            c.job = nextEdge(M, c.p, ci);
            if (c.job < 0) break;
            taken[c.job] = 1;
            c.from = c.p;
            c.t = 0;
          }
          const { a, b } = M.e[c.job];
          const use = Math.min(left, (1 - c.t) * per);
          c.t += use / per;
          left -= use;
          // First fifth of the time is the hop, the rest is the trace.
          const tr = Math.max(0, (c.t - 0.2) / 0.8);
          built[c.job] = tr;
          c.p = c.t < 0.2 ? lerp3(c.from, M.v[a], c.t / 0.2) : lerp3(M.v[a], M.v[b], tr);
          if (c.t >= 1 - 1e-6) {
            built[c.job] = 1;
            heat[c.job] = now;
            // Now and then a shard of light flies in from outside and locks onto the new edge.
            if (!still && shards.length < 90 && Math.random() < (36 * BUILD) / M.e.length) {
              const to = lerp3(M.v[a], M.v[b], 0.5);
              const o = norm2(to);
              const d = 0.25 + Math.random() * 0.35;
              shards.push({ to, from: [to[0] + o[0] * d + (Math.random() - 0.5) * 0.2, to[1] + (Math.random() - 0.2) * 0.4, to[2] + o[1] * d + (Math.random() - 0.5) * 0.2], born: now, size: 2 + Math.random() * 2.5 });
            }
            done++;
            c.job = -1;
          }
        }
      });
      if (yn) frontY += (ys / yn - frontY) * Math.min(1, dt * 3);
      // Wisps rise and curl like smoke; each keeps a short history so it draws as a ribbon.
      for (const w of wisps) {
        const age = now - w.born;
        const p = w.h[w.h.length - 1];
        const curl = 0.12 + 0.1 * age;
        w.h.push([p[0] + (w.v[0] + curl * Math.sin(age * 2.6 + w.seed)) * dt, p[1] + w.v[1] * dt, p[2] + (w.v[2] + curl * Math.cos(age * 2.1 + w.seed)) * dt]);
        if (w.h.length > 22) w.h.shift();
      }
      wisps = wisps.filter((w) => now - w.born < w.life);
      for (const s of sparks) {
        s.v[1] -= 2.6 * dt;
        s.p = [s.p[0] + s.v[0] * dt, s.p[1] + s.v[1] * dt, s.p[2] + s.v[2] * dt];
      }
      sparks = sparks.filter((s) => now - s.born < s.life);
      shards = shards.filter((s) => now - s.born < 0.75);
      if (phase === 'arrive' && phaseT > ARRIVE) {
        phase = 'build';
        phaseT = 0;
      } else if (phase === 'build' && done >= built.length) {
        phase = 'hold';
        phaseT = 0;
      } else if (phase === 'hold' && phaseT > (solid(M) ? REZ + SHOWN : HOLD)) {
        phase = 'fade';
        phaseT = 0;
      } else if (phase === 'fade' && phaseT > FADE) {
        mi = (mi + 1) % MODELS.length;
        startModel();
      }
      glyphs = glyphs.filter((g) => now - g.born < GLYPH);
      thoughts = thoughts.filter((g) => now - g.born < 1.4);
    };

    const project = (p) => {
      const cy = Math.cos(view.yaw);
      const sy = Math.sin(view.yaw);
      const cp = Math.cos(view.pitch);
      const sp = Math.sin(view.pitch);
      const x = p[0] * cy - p[2] * sy;
      const z1 = p[0] * sy + p[2] * cy;
      const y = p[1] * cp - z1 * sp;
      const z = p[1] * sp + z1 * cp;
      const s = Math.min(W, H) * 0.42 * MODELS[mi].zoom;
      const k = 3.4 / (3.4 + z);
      return [W / 2 + x * s * k, H / 2 - y * s * k, z];
    };
    // A direction turned into view space (no projection).
    const turn = (p) => {
      const cy = Math.cos(view.yaw);
      const sy = Math.sin(view.yaw);
      const cp = Math.cos(view.pitch);
      const sp = Math.sin(view.pitch);
      const z1 = p[0] * sy + p[2] * cy;
      return [p[0] * cy - p[2] * sy, p[1] * cp - z1 * sp, p[1] * sp + z1 * cp];
    };

    const draw = (nowMs) => {
      const now = nowMs / 1000;
      resize();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const M = MODELS[mi];
      const pts = M.v.map(project);
      const fade = phase === 'fade' ? 1 - phaseT / FADE : 1;
      // Once the wireframe is done, the solid model rezzes in from the ground up.
      const S = solid(M);
      const rez = S && !still ? (phase === 'hold' ? Math.min(1, phaseT / REZ) : phase === 'fade' ? 1 : 0) : S && still ? 1 : 0;
      if (gl) {
        gl.viewport(0, 0, glc.width, glc.height);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        if (S && rez > 0) {
          gl.useProgram(prog);
          gl.enable(gl.DEPTH_TEST);
          gl.enable(gl.BLEND);
          gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
          const s = Math.min(W, H) * 0.42 * M.zoom;
          const u = (n) => gl.getUniformLocation(prog, n);
          gl.uniform4f(u('uView'), Math.cos(view.yaw), Math.sin(view.yaw), Math.cos(view.pitch), Math.sin(view.pitch));
          gl.uniform2f(u('uScale'), (s * 2) / W, (s * 2) / H);
          gl.uniform1f(u('uReveal'), -1.05 + 2.2 * (1 - Math.pow(1 - rez, 2)));
          gl.uniform1f(u('uAlpha'), fade);
          gl.uniform3fv(u('uGlow'), rgbOf(accent));
          gl.uniform3fv(u('uCore'), rgbOf(dark ? core : '#FFF1D6'));
          const attr = (name, b, size, type, normalized) => {
            const l = gl.getAttribLocation(prog, name);
            gl.bindBuffer(gl.ARRAY_BUFFER, b);
            gl.enableVertexAttribArray(l);
            gl.vertexAttribPointer(l, size, type, normalized, 0, 0);
          };
          attr('aPos', S.pos, 3, gl.FLOAT, false);
          attr('aNrm', S.nrm, 3, gl.BYTE, true);
          attr('aCol', S.col, 3, gl.UNSIGNED_BYTE, true);
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, S.idx);
          gl.drawElements(gl.TRIANGLES, S.count, S.type, 0);
        }
      }
      // The wire steps back once the solid model is in.
      const wire = 1 - 0.75 * rez;

      // Which faces point at the camera (it sits at z = -3.4 in view space).
      const seen = new Uint8Array(M.fn.length);
      for (let f = 0; f < seen.length; f++) {
        if (M.two[f]) seen[f] = 1;
        else {
          const n = turn(M.fn[f]);
          const c = turn(M.fc[f]);
          seen[f] = n[0] * c[0] + n[1] * c[1] + n[2] * (c[2] + 3.4) < 0 ? 1 : 0;
        }
      }

      // Edges batched into a few paths: three depth bands for the near side, one faint path for
      // the far side. The edge being traced is drawn up to its tracer. During the fade, edges
      // drop out one by one instead of all at once.
      const bands = [new Path2D(), new Path2D(), new Path2D()];
      const back = new Path2D();
      for (let k = 0; k < M.e.length; k++) {
        const t = built[k];
        if (t <= 0) continue;
        if (phase === 'fade' && fade * 2 - ((k * 0.618) % 1) < 0.5) continue;
        const { a, b, f } = M.e[k];
        let front = f.length === 0;
        for (let j = 0; j < f.length && !front; j++) front = seen[f[j]] === 1;
        const A = pts[a];
        const B = pts[b];
        const path = front ? bands[Math.max(0, Math.min(2, Math.floor((A[2] + B[2] + 2) * 0.75)))] : back;
        path.moveTo(A[0], A[1]);
        path.lineTo(A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t);
      }
      ctx.lineCap = 'round';
      ctx.strokeStyle = accent;
      ctx.lineWidth = 0.8;
      ctx.globalAlpha = 0.06 * fade * (1 - rez);
      ctx.stroke(back);
      const peak = dark ? 0.9 : 0.95;
      [1, 0.7, 0.45].forEach((d, i) => {
        ctx.globalAlpha = peak * d * wire * fade;
        ctx.stroke(bands[i]);
      });

      // Fresh work glows: edges finished in the last moment burn bright, then cool to the wire.
      const hot = new Path2D();
      const warm = new Path2D();
      for (let k = 0; k < M.e.length; k++) {
        const age = now - heat[k];
        if (age > 0.9) continue;
        const { a, b } = M.e[k];
        const P = age < 0.3 ? hot : warm;
        P.moveTo(pts[a][0], pts[a][1]);
        P.lineTo(pts[b][0], pts[b][1]);
      }
      ctx.shadowColor = accent;
      ctx.shadowBlur = dark ? 10 : 5;
      ctx.lineWidth = 1.3;
      ctx.globalAlpha = 0.55 * fade;
      ctx.stroke(warm);
      ctx.lineWidth = 1.6;
      ctx.globalAlpha = fade;
      ctx.stroke(hot);
      ctx.shadowBlur = 0;
      ctx.strokeStyle = core;
      ctx.lineWidth = 0.6;
      ctx.stroke(hot);
      ctx.strokeStyle = accent;

      // The scan ring: a thin ring of light round the model at the build line.
      if (phase === 'build' && frontY > -1) {
        const r = reach(M, frontY) + 0.08;
        const ring = new Path2D();
        for (let k = 0; k <= 64; k++) {
          const a = (k / 64) * Math.PI * 2;
          const [x, y] = project([Math.cos(a) * r, frontY, Math.sin(a) * r]);
          if (k) ring.lineTo(x, y);
          else ring.moveTo(x, y);
        }
        ctx.shadowBlur = dark ? 8 : 3;
        ctx.lineWidth = 0.9;
        ctx.globalAlpha = 0.4;
        ctx.stroke(ring);
        // Light racing round the ring: a few bright comets, some each way, at different speeds,
        // each with a fading tail.
        ctx.shadowBlur = dark ? 14 : 5;
        for (const [speed, offset] of [[2.1, 0], [2.1, Math.PI], [-1.5, 0.8], [-1.5, 0.8 + Math.PI]]) {
          const head = now * speed + offset;
          const dir = Math.sign(speed);
          const tail = 0.9;
          let prev = null;
          for (let k = 0; k <= 16; k++) {
            const a = head - dir * tail * (1 - k / 16);
            const P = project([Math.cos(a) * r, frontY, Math.sin(a) * r]);
            if (prev) {
              const f = k / 16;
              ctx.globalAlpha = 0.9 * f * f;
              ctx.lineWidth = 0.6 + 1.8 * f;
              ctx.beginPath();
              ctx.moveTo(prev[0], prev[1]);
              ctx.lineTo(P[0], P[1]);
              ctx.stroke();
            }
            prev = P;
          }
          ctx.fillStyle = core;
          ctx.globalAlpha = 1;
          ctx.beginPath();
          ctx.arc(prev[0], prev[1], 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.shadowBlur = 0;
      }

      // Wisps: soft curling ribbons of smoke, batched by age into a few paths.
      const wispPaths = [new Path2D(), new Path2D(), new Path2D()];
      for (const w of wisps) {
        if (w.h.length < 3) continue;
        const band = Math.min(2, Math.floor(((now - w.born) / w.life) * 3));
        const P = wispPaths[band];
        const q = w.h.filter((_, i) => i % 3 === 0 || i === w.h.length - 1).map(project);
        P.moveTo(q[0][0], q[0][1]);
        for (let i = 1; i < q.length - 1; i++) P.quadraticCurveTo(q[i][0], q[i][1], (q[i][0] + q[i + 1][0]) / 2, (q[i][1] + q[i + 1][1]) / 2);
        P.lineTo(q[q.length - 1][0], q[q.length - 1][1]);
      }
      // Along the curls, small motes of light that drift up from where the beam lands.
      ctx.globalCompositeOperation = dark ? 'lighter' : 'source-over';
      for (const w of wisps) {
        const life = (now - w.born) / w.life;
        const n = w.h.length;
        for (let i = n - 1; i >= 0; i -= 3) {
          const [x, y] = project(w.h[i]);
          const r = 1.2 + 2.6 * (i / 21) + 1.5 * life;
          ctx.globalAlpha = (dark ? 0.3 : 0.22) * (1 - life) * (0.3 + 0.7 * (i / n)) * fade;
          ctx.drawImage(puff, x - r, y - r, r * 2, r * 2);
        }
      }
      ctx.globalCompositeOperation = 'source-over';
      ctx.lineWidth = 0.8;
      [0.22, 0.12, 0.05].forEach((al, i) => {
        ctx.globalAlpha = al * fade;
        ctx.stroke(wispPaths[i]);
      });

      // Trails: each agent leaves a tapering streak behind it.
      for (const c of crew) {
        const tp = c.trail.map(project);
        for (let i = 1; i < tp.length; i++) {
          const f = i / tp.length;
          ctx.globalAlpha = (phase === 'build' ? 0.5 : 0.15) * f * f;
          ctx.lineWidth = 0.5 + 2 * f;
          ctx.beginPath();
          ctx.moveTo(tp[i - 1][0], tp[i - 1][1]);
          ctx.lineTo(tp[i][0], tp[i][1]);
          ctx.stroke();
        }
      }

      // Beams: each working agent fires a laser down to the edge it is drawing: a wide red-orange
      // glow with a white-hot core, a bright point where it lands, and a faint column of light
      // rising above the agent, as if fed from overhead.
      ctx.lineCap = 'round';
      for (const c of crew) {
        if (phase !== 'build' || c.job < 0) continue;
        const E = project(c.em);
        const Pt = project(c.p);
        const flick = 0.85 + 0.15 * Math.sin(now * 40 + c.p[0] * 9);
        const col = ctx.createLinearGradient(E[0], E[1], E[0], 0);
        col.addColorStop(0, laser);
        col.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.2;
        ctx.globalAlpha = (dark ? 0.22 : 0.18) * flick;
        ctx.beginPath();
        ctx.moveTo(E[0], E[1]);
        ctx.lineTo(E[0], 0);
        ctx.stroke();
        ctx.strokeStyle = laser;
        ctx.shadowColor = laser;
        ctx.shadowBlur = dark ? 12 : 5;
        ctx.globalAlpha = 0.5 * flick;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(E[0], E[1]);
        ctx.lineTo(Pt[0], Pt[1]);
        ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.strokeStyle = core;
        ctx.globalAlpha = 0.95;
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.fillStyle = core;
        ctx.shadowColor = laser;
        ctx.shadowBlur = dark ? 14 : 5;
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(Pt[0], Pt[1], 1.8 + 0.8 * flick, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
      ctx.strokeStyle = accent;
      ctx.shadowColor = accent;

      // Sparks: short streaks that spray out from the contact point and fall away.
      if (sparks.length) {
        const hotS = new Path2D();
        const coolS = new Path2D();
        for (const sp of sparks) {
          const life = (now - sp.born) / sp.life;
          const A = project(sp.p);
          const B = project([sp.p[0] - sp.v[0] * 0.035, sp.p[1] - sp.v[1] * 0.035, sp.p[2] - sp.v[2] * 0.035]);
          const P = life < 0.5 ? hotS : coolS;
          P.moveTo(A[0], A[1]);
          P.lineTo(B[0], B[1]);
        }
        ctx.globalCompositeOperation = dark ? 'lighter' : 'source-over';
        ctx.lineWidth = 1;
        ctx.strokeStyle = laser;
        ctx.globalAlpha = 0.45;
        ctx.stroke(coolS);
        ctx.strokeStyle = core;
        ctx.globalAlpha = 0.9;
        ctx.stroke(hotS);
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = accent;
      }

      // Shards: small cubes of light that fly in, lock onto a fresh edge with a flash, and vanish.
      if (shards.length) {
        const body = new Path2D();
        const flash = new Path2D();
        for (const sh of shards) {
          const age = (now - sh.born) / 0.75;
          const u = Math.min(1, age / 0.6);
          const e = 1 - Math.pow(1 - u, 3);
          const [x, y] = project(lerp3(sh.from, sh.to, e));
          const r = sh.size * (u < 1 ? 1 : 1 - (age - 0.6) / 0.4);
          if (r <= 0.2) continue;
          // A tiny cube: a square with its top and side faces offset, read as a voxel.
          const P = u < 1 ? body : flash;
          P.rect(x - r, y - r, r * 2, r * 2);
          P.moveTo(x - r, y - r);
          P.lineTo(x - r * 0.4, y - r * 1.6);
          P.lineTo(x + r * 1.6, y - r * 1.6);
          P.lineTo(x + r * 1.6, y + r * 0.4);
          P.lineTo(x + r, y + r);
          P.moveTo(x + r, y - r);
          P.lineTo(x + r * 1.6, y - r * 1.6);
        }
        ctx.shadowColor = accent;
        ctx.shadowBlur = dark ? 8 : 3;
        ctx.lineWidth = 0.8;
        ctx.strokeStyle = accent;
        ctx.globalAlpha = 0.85 * fade;
        ctx.stroke(body);
        ctx.fillStyle = accent;
        ctx.globalAlpha = 0.18 * fade;
        ctx.fill(body);
        ctx.strokeStyle = core;
        ctx.globalAlpha = fade;
        ctx.stroke(flash);
        ctx.shadowBlur = 0;
        ctx.strokeStyle = accent;
      }

      // The crew: bright points with a soft glow that pulses.
      ctx.fillStyle = accent;
      crew.forEach((c, i) => {
        const [x, y] = project(c.em);
        const pulse = 0.5 + 0.5 * Math.sin(now * 6 + i * 1.7);
        ctx.shadowBlur = (dark ? 10 : 4) + 6 * pulse;
        ctx.globalAlpha = 0.95;
        ctx.beginPath();
        ctx.arc(x, y, 2.2 + 0.6 * pulse, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.shadowBlur = 0;

      // Code generation: each agent types a line out beside it, on the side away from the
      // model's centre, then the line drifts up and fades.
      ctx.font = `10.5px ${fonts.mono}`;
      ctx.fillStyle = accent;
      const mid = project([0, 0, 0]);
      for (const g of glyphs) {
        const age = now - g.born;
        const [x, y] = project(g.c.em);
        if (!g.side) g.side = x < mid[0] ? -1 : 1;
        const shown = Math.min(g.text.length, Math.floor(age * 34));
        const caret = shown < g.text.length || Math.floor(age * 4) % 2 ? '▌' : '';
        const text = g.text.slice(0, shown) + caret;
        if (!g.at) g.at = [x, y];
        // Follows its agent while typing, then lets go and rises.
        if (shown < g.text.length) g.at = [x, y];
        const rise = Math.max(0, age - g.text.length / 34) * 10;
        ctx.globalAlpha = Math.min(1, age * 6) * Math.max(0, Math.min(1, (GLYPH - age) / 0.8)) * 0.85 * fade;
        // Kept inside the canvas.
        const tw = ctx.measureText(g.text + '▌').width;
        const tx = g.side < 0 ? Math.max(6, g.at[0] - 10 - tw) : Math.min(W - 6 - tw, g.at[0] + 10);
        ctx.fillText(text, tx, Math.max(14, g.at[1] - 8 - rise));
      }
      // Thinking blocks: flicker in beside the idle agent, cell by cell, then fade.
      for (const g of thoughts) {
        const age = now - g.born;
        const [x, y] = project(g.c.em);
        const flick = age < 0.25 ? (Math.floor(age * 30) % 2 ? 0.3 : 0.9) : 1;
        const shown = Math.min(g.cells.length, Math.floor(age * 40));
        ctx.globalAlpha = Math.max(0, 0.8 * (1 - age / 1.4)) * flick;
        const ox = Math.min(W - 40, x + g.dx);
        for (let i = 0; i < shown; i++) ctx.fillRect(ox + g.cells[i][0] * 4, y + g.dy + g.cells[i][1] * 4, 3, 3);
      }

      ctx.globalAlpha = 1;
    };

    let raf = 0;
    let last = performance.now();
    let visible = true;
    const loopFn = (nowMs) => {
      const dt = Math.min(0.05, (nowMs - last) / 1000);
      last = nowMs;
      step(dt, nowMs / 1000);
      draw(nowMs);
      if (visible) raf = requestAnimationFrame(loopFn);
    };
    const io = new IntersectionObserver(([en]) => {
      visible = en.isIntersecting;
      cancelAnimationFrame(raf);
      if (visible && !still) {
        last = performance.now();
        raf = requestAnimationFrame(loopFn);
      }
    });
    io.observe(canvas);
    const ro = new ResizeObserver(() => draw(performance.now()));
    ro.observe(canvas);
    if (still) draw(performance.now());

    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      ro.disconnect();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onUp);
    };
  }, [accent, core, dark, laser]);

  return (
    <>
    <canvas
      ref={glRef}
      aria-hidden="true"
      style={{ position: 'absolute', top: 0, right: 0, height: '100%', width: '38%', zIndex: 2, pointerEvents: 'none' }}
      className="hero-forge-solid"
    />
    <canvas
      ref={ref}
      aria-hidden="true"
      style={{ position: 'absolute', top: 0, right: 0, height: '100%', width: '38%', zIndex: 2, cursor: 'grab', touchAction: 'pan-y' }}
      className="hero-forge"
    />
    </>
  );
}
