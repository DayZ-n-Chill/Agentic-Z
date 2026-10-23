import { useId } from 'react';
import { Box } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import { fonts } from '../theme.js';

// A hand-placed flow diagram drawn as SVG: boxes, groups and orthogonal arrows, so a diagram can show
// branches, merges and loop-backs instead of a straight list of steps.
//
// spec = {
//   width, height,                       viewBox size; the drawing scales to the column and scrolls on phones
//   lanes:  [{ y, label, sub }],         optional row labels on the left
//   groups: [{ x, y, w, h, label }],     shaded areas behind a set of nodes
//   nodes:  [{ id, x, y, w, h, label, detail, accent, mono, small }],
//   edges:  [{ from, to, fs, ts, via, label, lx, ly, anchor, loop, soft, noArrow, fo, to_ }] or [{ pts: [[x, y], ...] }],
//   notes:  [{ x, y, text, anchor, rotate, loop }],
// }
// fs / ts are the sides an edge leaves and enters: t, r, b, l; fo / to_ shift the point along that side.
// via lists corner points; pts draws a line through fixed points instead of between two nodes.
// loop draws the edge dashed in the accent color (work going back); soft draws it dashed and quiet.

const sidePoint = (n, side, off = 0) => {
  switch (side) {
    case 't':
      return [n.x + n.w / 2 + off, n.y];
    case 'b':
      return [n.x + n.w / 2 + off, n.y + n.h];
    case 'l':
      return [n.x, n.y + n.h / 2 + off];
    default:
      return [n.x + n.w, n.y + n.h / 2 + off];
  }
};

function route(a, b, fs, via) {
  if (via) return [a, ...via, b];
  if (a[0] === b[0] || a[1] === b[1]) return [a, b];
  if (fs === 'l' || fs === 'r') {
    const mx = (a[0] + b[0]) / 2;
    return [a, [mx, a[1]], [mx, b[1]], b];
  }
  const my = (a[1] + b[1]) / 2;
  return [a, [a[0], my], [b[0], my], b];
}

export default function Graph({ spec }) {
  const t = useTheme();
  const uid = useId().replace(/:/g, '');
  const dark = t.palette.mode === 'dark';
  const c = {
    line: alpha(t.palette.text.primary, dark ? 0.45 : 0.5),
    soft: alpha(t.palette.text.primary, dark ? 0.3 : 0.35),
    box: alpha(t.palette.text.primary, dark ? 0.22 : 0.28),
    accent: t.palette.primary.main,
    text: t.palette.text.primary,
    sub: t.palette.text.secondary,
    paper: t.palette.background.paper,
    group: alpha(t.palette.text.primary, dark ? 0.035 : 0.03),
  };
  const byId = Object.fromEntries(spec.nodes.map((n) => [n.id, n]));
  const marker = (name, color) => (
    <marker id={`${uid}-${name}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,1 L9,5 L0,9 z" fill={color} />
    </marker>
  );

  return (
    // Focusable so keyboard users can scroll a wide diagram on a narrow screen.
    <Box tabIndex={0} sx={{ overflowX: 'auto', mx: { xs: -0.5, sm: 0 }, borderRadius: 1, '&:focus-visible': { outline: 2, outlineColor: 'primary.main', outlineOffset: 2 } }}>
      <Box
        component="svg"
        viewBox={`0 0 ${spec.width} ${spec.height}`}
        role="img"
        aria-label={spec.alt}
        sx={{ display: 'block', width: '100%', minWidth: spec.minWidth || 640, height: 'auto' }}
      >
        <defs>
          {marker('a', c.line)}
          {marker('l', c.accent)}
          {marker('s', c.soft)}
        </defs>

        {(spec.lanes || []).map((l) => (
          <g key={l.label} fontFamily={fonts.mono}>
            <text x={spec.laneX || 78} y={l.y} textAnchor="end" fontSize="10.5" letterSpacing="1.2" fill={c.sub}>
              {l.label.toUpperCase()}
            </text>
            {l.sub && (
              <text x={spec.laneX || 78} y={l.y + 15} textAnchor="end" fontSize="11" fill={c.sub} fontFamily={fonts.body}>
                {l.sub}
              </text>
            )}
          </g>
        ))}

        {(spec.groups || []).map((g) => (
          <g key={g.label || `${g.x}-${g.y}`}>
            <rect x={g.x} y={g.y} width={g.w} height={g.h} rx="10" fill={c.group} stroke={c.soft} strokeDasharray={g.dashed ? '4 4' : undefined} />
            {g.label && (
              <text x={g.x + 12} y={g.y + 18} fontFamily={fonts.mono} fontSize="10" letterSpacing="1.2" fill={c.sub}>
                {g.label.toUpperCase()}
              </text>
            )}
          </g>
        ))}

        {spec.edges.map((e, i) => {
          const pts = e.pts || route(sidePoint(byId[e.from], e.fs || 'r', e.fo || 0), sidePoint(byId[e.to], e.ts || 'l', e.to_ || 0), e.fs || 'r', e.via);
          const color = e.loop ? c.accent : e.soft ? c.soft : c.line;
          return (
            <g key={i}>
              <polyline
                points={pts.map((p) => p.join(',')).join(' ')}
                fill="none"
                stroke={color}
                strokeWidth={e.loop ? 1.6 : 1.4}
                strokeDasharray={e.loop || e.soft ? '5 4' : undefined}
                strokeLinejoin="round"
                markerEnd={e.noArrow ? undefined : `url(#${uid}-${e.loop ? 'l' : e.soft ? 's' : 'a'})`}
              />
              {e.label && (
                <text
                  x={e.lx}
                  y={e.ly}
                  textAnchor={e.anchor || 'start'}
                  fontFamily={fonts.body}
                  fontSize="11.5"
                  fill={e.loop ? c.accent : c.sub}
                >
                  {e.label}
                </text>
              )}
            </g>
          );
        })}

        {spec.nodes.map((n) => {
          const lines = n.detail ? n.detail.split('\n') : [];
          const cy = n.y + n.h / 2 - (lines.length * 15) / 2 + 5;
          return (
            <g key={n.id}>
              <rect
                x={n.x}
                y={n.y}
                width={n.w}
                height={n.h}
                rx="8"
                fill={n.accent ? alpha(c.accent, dark ? 0.12 : 0.08) : c.paper}
                stroke={n.accent ? c.accent : c.box}
                strokeWidth={n.accent ? 1.5 : 1.2}
              />
              <text
                x={n.x + n.w / 2}
                y={cy}
                textAnchor="middle"
                fontFamily={n.mono ? fonts.mono : fonts.display}
                fontWeight={n.small ? 500 : 600}
                fontSize={n.small ? 12.5 : n.mono ? 13 : 14.5}
                fill={n.accent ? c.accent : c.text}
              >
                {n.label}
              </text>
              {lines.map((l, i) => (
                <text
                  key={i}
                  x={n.x + n.w / 2}
                  y={cy + 17 + i * 15}
                  textAnchor="middle"
                  fontFamily={l.startsWith('/') || l.includes('_') ? fonts.mono : fonts.body}
                  fontSize="11.5"
                  fill={c.sub}
                >
                  {l}
                </text>
              ))}
            </g>
          );
        })}

        {(spec.notes || []).map((n, i) => (
          <text
            key={i}
            x={n.x}
            y={n.y}
            textAnchor={n.anchor || 'start'}
            transform={n.rotate ? `rotate(${n.rotate} ${n.x} ${n.y})` : undefined}
            fontFamily={fonts.body}
            fontSize="11.5"
            fill={n.loop ? c.accent : c.sub}
          >
            {n.text}
          </text>
        ))}
      </Box>
    </Box>
  );
}
