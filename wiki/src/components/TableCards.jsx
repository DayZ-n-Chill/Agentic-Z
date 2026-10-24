import { Box, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { fonts } from '../theme.js';

// Markdown tables rendered as cards, in the same style as the skills page.
// Bold-only rows ("| **Build** | |") start a new card. Short-value columns (grades, status) become chips.

function cells(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split(/(?<!\\)\|/)
    .map((c) => c.trim());
}

export function parseTable(md) {
  const lines = md.trim().split('\n');
  const header = cells(lines[0]);
  const groups = [{ title: '', rows: [] }];
  for (const line of lines.slice(2)) {
    const row = cells(line);
    const cat = row[0].match(/^\*\*(.+)\*\*$/);
    if (cat && row.slice(1).every((c) => !c)) groups.push({ title: cat[1], rows: [] });
    else groups[groups.length - 1].rows.push(row);
  }
  return { header, groups: groups.filter((g) => g.rows.length) };
}

const plain = (s) => s.replace(/[`*]/g, '');

// Subtle report-card colors: A green, B teal, C amber, D orange, F red. Anything else stays neutral.
const GRADE_HUES = {
  A: { dark: '#6FBF73', light: '#2A7230' },
  B: { dark: '#5FB3B3', light: '#1F6F6F' },
  C: { dark: '#E2A33B', light: '#8A520A' },
  D: { dark: '#E07B3C', light: '#9E4914' },
  F: { dark: '#E5645A', light: '#B3261E' },
};

function chipSx(t, value) {
  const v = plain(value);
  const hue = /^[A-DF][+-]?$/.test(v) && GRADE_HUES[v[0]]?.[t.palette.mode];
  const muted = v === 'not built' || v === 'n/a' || !v;
  return {
    fontFamily: fonts.mono,
    fontSize: '0.74rem',
    fontWeight: 500,
    px: 0.75,
    py: 0.1,
    borderRadius: 0.75,
    border: 1,
    whiteSpace: 'nowrap',
    borderColor: hue ? alpha(hue, 0.35) : 'divider',
    bgcolor: hue ? alpha(hue, t.palette.mode === 'dark' ? 0.12 : 0.08) : alpha(t.palette.text.primary, 0.05),
    color: hue || (muted ? 'text.secondary' : 'text.primary'),
  };
}

function ValueChip({ label, value }) {
  return (
    <Stack direction="row" alignItems="center" gap={0.75}>
      <Typography sx={{ fontFamily: fonts.mono, fontSize: '0.66rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'text.secondary' }}>
        {label}
      </Typography>
      <Box component="span" sx={(t) => chipSx(t, value)}>
        {plain(value) || '—'}
      </Box>
    </Stack>
  );
}

// "B+ to B-" or "A, A-": each grade as a tag, the joining words as plain text.
function GradeRange({ text }) {
  return (
    <Stack direction="row" alignItems="center" gap={0.75} sx={{ flexWrap: 'wrap' }}>
      {plain(text)
        .split(/(,\s*|\s+to\s+)/)
        .filter(Boolean)
        .map((tok, i) =>
          /^[A-DF][+-]?$/.test(tok) ? (
            <Box key={i} component="span" sx={(t) => chipSx(t, tok)}>
              {tok}
            </Box>
          ) : (
            <Typography key={i} component="span" variant="body2" color="text.secondary">
              {tok.trim().replace(/^,$/, '')}
            </Typography>
          )
        )}
    </Stack>
  );
}

export default function TableCards({ source, renderInline }) {
  const { header, groups } = parseTable(source);
  const n = header.length;
  // A column is "short" when every value fits in a chip: grades, statuses, versions.
  const short = header.map((_, c) => c > 0 && groups.every((g) => g.rows.every((r) => plain(r[c] || '').length <= 14)));
  const longCols = header.map((_, c) => c).filter((c) => c > 0 && !short[c]);
  // The grading scale ("| Grade | Meaning |") shows its grades as the same colored tags.
  const isScale = plain(header[0]) === 'Grade';
  const titleFromHeader = n === 2 && header[0].includes('`') ? plain(header[0]) : '';

  if (!longCols.length && short.some(Boolean)) return <Matrix header={header} groups={groups} renderInline={renderInline} />;

  return (
    <Stack gap={2} sx={{ my: 2.5 }}>
      {groups.map((g, gi) => {
        const title = g.title || (gi === 0 ? titleFromHeader : '');
        return (
          <Box key={gi} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden', bgcolor: 'background.paper' }}>
            {title && (
              <Typography
                variant="overline"
                color="text.secondary"
                component="div"
                sx={{ px: 1.75, py: 0.75, borderBottom: 1, borderColor: 'divider', bgcolor: (t) => alpha(t.palette.text.primary, 0.03) }}
              >
                {title} · {g.rows.length}
              </Typography>
            )}
            <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
              {g.rows.map((row, ri) => (
                <Box
                  component="li"
                  key={ri}
                  sx={{
                    px: 1.75,
                    py: 1.25,
                    borderTop: ri ? 1 : 0,
                    borderColor: 'divider',
                    display: 'grid',
                    gap: { xs: 0.5, sm: 2 },
                    gridTemplateColumns: { xs: '1fr', sm: '220px minmax(0, 1fr)' },
                  }}
                >
                  <Box
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      lineHeight: 1.5,
                      overflowWrap: 'break-word',
                      '& p': { m: 0, font: 'inherit' },
                      // Names in code read like the skills page: amber mono, no box.
                      '& code': { bgcolor: 'transparent', border: 0, p: 0, color: 'primary.main', fontSize: '0.8rem', fontWeight: 500 },
                      // A name followed by IDs ("**Script engineer** `dayz-...`") puts each ID on its own line.
                      '& strong ~ code': { display: 'block', mt: 0.25 },
                    }}
                  >
                    {isScale ? <GradeRange text={row[0]} /> : renderInline(row[0])}
                  </Box>
                  <Stack gap={0.75} sx={{ minWidth: 0 }}>
                    {longCols.map((c, k) =>
                      row[c] ? (
                        <Box key={c}>
                          {k > 0 && (
                            <Typography
                              sx={{ fontFamily: fonts.mono, fontSize: '0.66rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'text.secondary', mb: 0.25 }}
                            >
                              {plain(header[c])}
                            </Typography>
                          )}
                          <Typography
                            variant="body2"
                            component="div"
                            color={k === 0 ? 'text.primary' : 'text.secondary'}
                            sx={{ lineHeight: 1.6, '& p': { m: 0, font: 'inherit', color: 'inherit' } }}
                          >
                            {renderInline(row[c])}
                          </Typography>
                        </Box>
                      ) : null
                    )}
                    {short.some(Boolean) && (
                      <Stack direction="row" gap={2} sx={{ flexWrap: 'wrap', rowGap: 0.75 }}>
                        {header.map((h, c) => (short[c] ? <ValueChip key={c} label={plain(h)} value={row[c] || ''} /> : null))}
                      </Stack>
                    )}
                  </Stack>
                </Box>
              ))}
            </Box>
          </Box>
        );
      })}
    </Stack>
  );
}

// Tables whose other columns are all short (grades, statuses): one even column per value.
function Matrix({ header, groups, renderInline }) {
  const cols = header.length - 1;
  // Wide enough for the longest column header on one line (about 7.5px per character at this size),
  // capped so long headers wrap instead of squeezing the name column.
  const colWidth = Math.min(136, Math.max(112, Math.ceil(Math.max(...header.slice(1).map((h) => plain(h).length)) * 7.5) + 8));
  const grid = {
    display: 'grid',
    alignItems: 'center',
    columnGap: 2,
    rowGap: 0.75,
    gridTemplateColumns: { xs: `repeat(${cols}, minmax(0, 1fr))`, sm: `minmax(220px, 1fr) repeat(${cols}, ${colWidth}px)` },
  };
  const nameSx = { gridColumn: { xs: '1 / -1', sm: 'auto' } };
  return (
    <Stack gap={2} sx={{ my: 2.5 }}>
      {groups.map((g, gi) => (
        <Box key={gi} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden', bgcolor: 'background.paper' }}>
          <Box sx={(t) => ({ ...grid, px: 1.75, py: 0.75, borderBottom: 1, borderColor: 'divider', bgcolor: alpha(t.palette.text.primary, 0.03) })}>
            <Typography variant="overline" color="text.secondary" sx={{ ...nameSx, lineHeight: 1.6 }}>
              {g.title ? `${g.title} · ${g.rows.length}` : plain(header[0])}
            </Typography>
            {header.slice(1).map((h) => {
              // On phones only the first word shows ("v1.5.0"), so every header stays on one line.
              const [first, ...rest] = plain(h).split(' ');
              return (
                <Typography key={h} sx={{ fontFamily: fonts.mono, fontSize: '0.64rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'text.secondary', lineHeight: 1.3, whiteSpace: { xs: 'nowrap', sm: 'normal' } }}>
                  {first}
                  {rest.length > 0 && <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}> {rest.join(' ')}</Box>}
                </Typography>
              );
            })}
          </Box>
          <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
            {g.rows.map((row, ri) => (
              <Box component="li" key={ri} sx={{ ...grid, px: 1.75, py: 1, borderTop: ri ? 1 : 0, borderColor: 'divider' }}>
                <Box
                  sx={{
                    ...nameSx,
                    minWidth: 0,
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    overflowWrap: 'break-word',
                    '& p': { m: 0, font: 'inherit' },
                    '& code': { bgcolor: 'transparent', border: 0, p: 0, color: 'primary.main', fontSize: '0.8rem', fontWeight: 500 },
                  }}
                >
                  {renderInline(row[0])}
                </Box>
                {row.slice(1, cols + 1).map((v, c) => (
                  <Box key={c}>
                    <Box component="span" sx={(t) => chipSx(t, v)}>
                      {plain(v) || '—'}
                    </Box>
                  </Box>
                ))}
              </Box>
            ))}
          </Box>
        </Box>
      ))}
    </Stack>
  );
}
