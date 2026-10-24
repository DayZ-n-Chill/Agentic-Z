import { useEffect, useRef } from 'react';
import { useTheme } from '@mui/material/styles';

// Ambient WebGL layer for the home card. It sits on top of the card's CSS grid and lights it:
//   - amber fog drifts slowly across the card and warms the grid lines it passes over;
//   - now and then a single cell blinks, like a node reporting in.
// The grid math uses the same 28px cells as the CSS background, so the glow lands on the real lines.
// Pauses offscreen, draws one still frame under prefers-reduced-motion, and renders nothing without WebGL.

const CELL = 28;

const VERT = `
attribute vec2 p;
void main() { gl_Position = vec4(p, 0.0, 1.0); }
`;

const FRAG = `
precision mediump float;
uniform vec2 uRes;
uniform float uDpr;
uniform float uTime;
uniform vec3 uColor;
uniform float uGain;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
  return v;
}

void main() {
  // CSS pixels, origin top-left, to match the background grid.
  vec2 px = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y) / uDpr;
  vec2 size = uRes / uDpr;
  vec2 uv = px / size.y;
  float t = uTime;

  // Fog: two layers of fbm drifting against each other, weighted toward the right side.
  vec2 q = vec2(fbm(uv * 1.6 + vec2(t * 0.020, -t * 0.013)), fbm(uv * 1.6 + vec2(5.2, 1.3) - t * 0.017));
  float fog = fbm(uv * 2.2 + q * 1.8 + vec2(-t * 0.03, 0.0));
  fog = smoothstep(0.42, 0.85, fog);
  fog *= mix(0.35, 1.0, smoothstep(0.0, 1.0, px.x / size.x));

  // Grid lines and crossings, 1px wide like the CSS grid.
  vec2 g = mod(px, ${CELL.toFixed(1)});
  float line = max(step(g.x, 1.0), step(g.y, 1.0));
  vec2 d = min(g, ${CELL.toFixed(1)} - g);
  float node = smoothstep(2.6, 0.0, length(d));

  // Blinking cells: one random cell per slot lights up and fades.
  vec2 cell = floor(px / ${CELL.toFixed(1)});
  float slot = floor(t * 0.7);
  float pick = hash(cell + slot * 13.1);
  float life = fract(t * 0.7);
  float blink = step(0.9965, pick) * sin(life * 3.14159) * (1.0 - line);

  float a = 0.0;
  a += fog * 0.09;                    // haze
  a += line * fog * 0.25;             // grid warmed by the fog
  a += node * fog * 0.12;
  a += blink * 0.10;
  a = clamp(a * uGain, 0.0, 1.0);
  gl_FragColor = vec4(uColor * a, a);
}
`;

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

export default function HeroShader() {
  const ref = useRef(null);
  const theme = useTheme();
  const dark = theme.palette.mode === 'dark';
  const color = theme.palette.primary.main;

  useEffect(() => {
    const canvas = ref.current;
    const gl = canvas && canvas.getContext('webgl', { premultipliedAlpha: true, antialias: false });
    if (!gl) return undefined;

    const compile = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
    };
    const vs = compile(gl.VERTEX_SHADER, VERT);
    const fs = compile(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return undefined;
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return undefined;
    gl.useProgram(prog);

    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const u = (name) => gl.getUniformLocation(prog, name);
    const uRes = u('uRes');
    const uDpr = u('uDpr');
    const uTime = u('uTime');
    gl.uniform3fv(u('uColor'), hexToRgb(color));
    gl.uniform1f(u('uGain'), dark ? 1.0 : 0.75);

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      const w = Math.round(canvas.clientWidth * dpr);
      const h = Math.round(canvas.clientHeight * dpr);
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
      gl.uniform2f(uRes, w, h);
      gl.uniform1f(uDpr, dpr);
    };

    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const start = performance.now();
    let raf = 0;
    let visible = true;
    const draw = (now) => {
      resize();
      gl.uniform1f(uTime, still ? 4.0 : (now - start) / 1000 + 4.0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!still && visible) raf = requestAnimationFrame(draw);
    };

    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      cancelAnimationFrame(raf);
      if (visible) raf = requestAnimationFrame(draw);
    });
    io.observe(canvas);
    const ro = new ResizeObserver(() => still && draw(0));
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      ro.disconnect();
      // No loseContext() here: React runs this effect twice in development (StrictMode), and the
      // second run gets the same canvas back, so a lost context left the hero blank until the
      // theme changed. A canvas that unmounts frees its context with it.
    };
  }, [color, dark]);

  return (
    <canvas
      key={color}
      ref={ref}
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }}
    />
  );
}
