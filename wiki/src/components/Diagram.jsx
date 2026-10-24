import { Box, LinearProgress, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ReplayIcon from '@mui/icons-material/Replay';
import { fonts } from '../theme.js';
import Graph from './Graph.jsx';

const mono = { fontFamily: fonts.mono, fontSize: '0.72rem' };

function Tag({ children }) {
  return (
    <Box
      component="span"
      sx={(t) => ({
        ...mono,
        display: 'inline-block',
        px: 0.75,
        py: 0.2,
        borderRadius: 0.75,
        border: 1,
        borderColor: 'divider',
        bgcolor: alpha(t.palette.text.primary, 0.04),
        overflowWrap: 'break-word',
        maxWidth: '100%',
      })}
    >
      {children}
    </Box>
  );
}

function Node({ step }) {
  return (
    <Box
      sx={(t) => ({
        flex: '1 1 150px',
        minWidth: 0,
        p: 1.5,
        borderRadius: 1,
        border: 1,
        borderColor: step.accent ? alpha(t.palette.primary.main, 0.7) : 'divider',
        bgcolor: step.accent ? alpha(t.palette.primary.main, 0.08) : 'background.paper',
      })}
    >
      <Typography
        sx={{
          fontFamily: step.label.startsWith('/') ? fonts.mono : fonts.display,
          fontWeight: 600,
          fontSize: step.label.startsWith('/') ? '0.82rem' : '0.95rem',
          lineHeight: 1.3,
          color: step.accent ? 'primary.main' : 'text.primary',
        }}
      >
        {step.label}
      </Typography>
      {step.items && (
        <Stack direction="row" gap={0.5} sx={{ flexWrap: 'wrap', mt: 1 }}>
          {step.items.map((it) => (
            <Tag key={it}>{it}</Tag>
          ))}
        </Stack>
      )}
      {step.detail && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, fontSize: '0.8rem', lineHeight: 1.45 }}>
          {step.detail}
        </Typography>
      )}
    </Box>
  );
}

function Loop({ text }) {
  return (
    <Stack direction="row" alignItems="center" gap={1} sx={{ mt: 1.5, color: 'primary.main' }}>
      <ReplayIcon sx={{ fontSize: 18 }} />
      <Typography sx={{ ...mono, fontSize: '0.75rem', letterSpacing: '0.04em' }}>{text}</Typography>
    </Stack>
  );
}

function Flow({ spec }) {
  const n = spec.steps.length;
  if (n > 4) {
    return (
      <>
        <Tiers spec={{ tiers: spec.steps, numbered: true }} />
        {spec.loop && <Loop text={spec.loop} />}
      </>
    );
  }
  return (
    <>
      <Box
        sx={{
          display: 'grid',
          gap: { xs: 3.5, sm: 3.5 },
          gridTemplateColumns: { xs: '1fr', sm: `repeat(${n}, minmax(0, 1fr))` },
        }}
      >
        {spec.steps.map((s, i) => (
          <Box key={s.label} sx={{ position: 'relative', display: 'flex' }}>
            <Node step={s} />
            {i < n - 1 && (
              <Box
                aria-hidden
                sx={{
                  position: 'absolute',
                  color: 'text.secondary',
                  display: 'grid',
                  placeItems: 'center',
                  right: { xs: 'auto', sm: -26 },
                  left: { xs: '50%', sm: 'auto' },
                  top: { xs: 'auto', sm: '50%' },
                  bottom: { xs: -26, sm: 'auto' },
                  transform: { xs: 'translateX(-50%)', sm: 'translateY(-50%)' },
                  width: 20,
                  height: 20,
                }}
              >
                <ArrowForwardIcon sx={{ fontSize: 18, display: { xs: 'none', sm: 'block' } }} />
                <ArrowDownwardIcon sx={{ fontSize: 18, display: { xs: 'block', sm: 'none' } }} />
              </Box>
            )}
          </Box>
        ))}
      </Box>
      {spec.loop && <Loop text={spec.loop} />}
    </>
  );
}

function Tiers({ spec }) {
  return (
    <Stack>
      {spec.tiers.map((tier, i) => (
        <Box key={tier.label}>
          {i > 0 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', color: 'text.secondary', py: 0.25 }} aria-hidden>
              <ArrowDownwardIcon sx={{ fontSize: 16 }} />
            </Box>
          )}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '210px minmax(0, 1fr)' },
              gap: { xs: 0.75, sm: 2 },
              alignItems: 'center',
              p: 1.5,
              borderRadius: 1,
              border: 1,
              borderColor: tier.accent ? 'primary.main' : 'divider',
              bgcolor: 'background.paper',
            }}
          >
            <Stack direction="row" alignItems="center" gap={1.25}>
              {spec.numbered && (
                <Box
                  sx={(t) => ({
                    ...mono,
                    width: 22,
                    height: 22,
                    flexShrink: 0,
                    display: 'grid',
                    placeItems: 'center',
                    borderRadius: '50%',
                    color: t.palette.primary.main,
                    bgcolor: alpha(t.palette.primary.main, 0.14),
                  })}
                >
                  {i + 1}
                </Box>
              )}
              <Typography
                sx={{
                  fontFamily: tier.label.startsWith('/') ? fonts.mono : fonts.display,
                  fontWeight: 600,
                  fontSize: tier.label.startsWith('/') ? '0.85rem' : '0.95rem',
                  color: tier.accent ? 'primary.main' : 'text.primary',
                }}
              >
                {tier.label}
              </Typography>
            </Stack>
            <Stack direction="row" gap={0.75} alignItems="center" sx={{ flexWrap: 'wrap' }}>
              {tier.items?.map((it) => (
                <Tag key={it}>{it}</Tag>
              ))}
              {tier.detail && (
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.82rem', ml: tier.items ? 0.5 : 0 }}>
                  {tier.detail}
                </Typography>
              )}
            </Stack>
          </Box>
        </Box>
      ))}
    </Stack>
  );
}

function Groups({ spec }) {
  return (
    <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' } }}>
      {spec.groups.map((g) => (
        <Box key={g.label} sx={{ p: 1.5, borderRadius: 1, border: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 600, fontSize: '0.95rem', mb: 1 }}>{g.label}</Typography>
          <Stack gap={0.5}>
            {g.items.map((it) => (
              <Typography key={it} sx={{ ...mono, fontSize: '0.78rem', color: 'primary.main', overflowWrap: 'anywhere' }}>
                + {it}
              </Typography>
            ))}
          </Stack>
        </Box>
      ))}
    </Box>
  );
}

function Versions({ spec }) {
  return (
    <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, minmax(0, 1fr))' } }}>
      {spec.versions.map((v, i) => (
        <Box
          key={v.label}
          sx={(t) => ({
            p: 1.75,
            borderRadius: 1,
            border: 1,
            borderColor: i === spec.versions.length - 1 ? alpha(t.palette.primary.main, 0.7) : 'divider',
            bgcolor: 'background.paper',
          })}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="baseline">
            <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: '1.15rem' }}>{v.label}</Typography>
            <Typography variant="overline" color="text.secondary">
              {v.note}
            </Typography>
          </Stack>
          <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: '1.9rem', lineHeight: 1.1, mt: 1, fontVariantNumeric: 'tabular-nums' }}>
            {v.top}
            <Box component="span" sx={{ fontSize: '0.9rem', color: 'text.secondary', fontWeight: 500, ml: 0.75 }}>
              of {v.built} at A+
            </Box>
          </Typography>
          <LinearProgress
            variant="determinate"
            value={v.built ? (v.top / v.built) * 100 : 0}
            aria-label={`${v.label} items at A+`}
            sx={(t) => ({ height: 4, borderRadius: 2, my: 1.25, bgcolor: alpha(t.palette.text.primary, 0.1) })}
          />
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
            {v.built} of {spec.total} items built{v.tests ? ` · ${v.tests}` : ''}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}

export default function Diagram({ spec, title }) {
  const Body = { flow: Flow, tiers: Tiers, groups: Groups, versions: Versions, graph: Graph }[spec.type];
  return (
    <Box
      component="figure"
      sx={(t) => ({
        m: 0,
        my: 3,
        p: { xs: 1.5, sm: 2.5 },
        borderRadius: 1.5,
        border: 1,
        borderColor: 'divider',
        bgcolor: alpha(t.palette.text.primary, 0.02),
        backgroundImage: `radial-gradient(${alpha(t.palette.text.primary, 0.08)} 1px, transparent 1px)`,
        backgroundSize: '16px 16px',
      })}
    >
      <Body spec={spec} />
      {(title || spec.caption) && (
        <Typography component="figcaption" variant="body2" color="text.secondary" sx={{ mt: 1.75, fontSize: '0.8rem' }}>
          {title && (
            <Box component="span" sx={{ ...mono, textTransform: 'uppercase', letterSpacing: '0.1em', mr: 1 }}>
              {title}
            </Box>
          )}
          {spec.caption}
        </Typography>
      )}
    </Box>
  );
}
