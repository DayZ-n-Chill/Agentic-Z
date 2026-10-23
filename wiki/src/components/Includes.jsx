import { Box, Button, Card, Link, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { skillGroups } from '../content.js';
import { fonts } from '../theme.js';

const SPECIALISTS = [
  'Scripts, configs and UI',
  'Models and textures',
  'Maps and servers',
  'Saved data and AI',
  'Vehicles and weapons',
  'Wearables and animation',
  'Audio, effects and physics',
  'Review and debugging',
];

const skillAnchor = (title) => `skills-${title.toLowerCase().replace(/[^a-z]+/g, '-')}`;

const RAG_SOURCES = ['Vanilla scripts', 'Configs', 'Layouts', 'Materials'];

function Summary({ count, unit, title, children, action }) {
  return (
    <Card variant="outlined" sx={{ p: 2.5, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <Typography variant="overline" color="text.secondary">
        {title}
      </Typography>
      <Stack direction="row" alignItems="baseline" gap={1} sx={{ mb: 1.5 }}>
        <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: '2.2rem', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
          {count}
        </Typography>
        <Typography color="text.secondary" fontSize="0.9rem">
          {unit}
        </Typography>
      </Stack>
      <Box sx={{ flex: 1 }}>{children}</Box>
      <Box sx={{ mt: 2 }}>{action}</Box>
    </Card>
  );
}

function Bullets({ items }) {
  return (
    <Stack component="ul" gap={0.5} sx={{ listStyle: 'none', p: 0, m: 0 }}>
      {items.map((it) => (
        <Box
          component="li"
          key={typeof it === 'string' ? it : it.key}
          sx={{
            fontSize: '0.88rem',
            display: 'flex',
            justifyContent: 'space-between',
            gap: 1,
            pl: 1.5,
            position: 'relative',
            '&::before': { content: '""', position: 'absolute', left: 0, top: '0.6em', width: 5, height: 5, bgcolor: 'primary.main' },
          }}
        >
          {typeof it === 'string' ? it : it.node}
        </Box>
      ))}
    </Stack>
  );
}

export default function Includes({ onNavigate }) {
  const total = skillGroups.reduce((n, g) => n + g.skills.length, 0);
  return (
    <Box sx={{ my: 3 }}>
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, minmax(0, 1fr))' } }}>
        <Summary
          title="Specialists"
          count={30}
          unit="agents"
          action={
            <Button size="small" endIcon={<ArrowForwardIcon />} onClick={() => onNavigate('agents')}>
              All agents
            </Button>
          }
        >
          <Bullets items={SPECIALISTS} />
        </Summary>
        <Summary
          title="Skills"
          count={total}
          unit="slash commands"
          action={
            <Button size="small" endIcon={<ArrowForwardIcon />} onClick={() => onNavigate('the-skills')}>
              All skills
            </Button>
          }
        >
          <Bullets
            items={skillGroups.map((g) => ({
              key: g.title,
              node: (
                <>
                  <Link
                    component="button"
                    underline="hover"
                    color="inherit"
                    onClick={() => onNavigate('the-skills', skillAnchor(g.title))}
                    sx={{ textAlign: 'left', fontSize: 'inherit' }}
                  >
                    {g.title}
                  </Link>
                  <Box component="span" sx={{ color: 'text.secondary', fontFamily: fonts.mono, fontSize: '0.8rem' }}>
                    {g.skills.length}
                  </Box>
                </>
              ),
            }))}
          />
        </Summary>
        <Summary
          title="RAG search"
          count={RAG_SOURCES.length}
          unit="vanilla sources"
          action={
            <Button size="small" endIcon={<ArrowForwardIcon />} onClick={() => onNavigate('rag-search')}>
              How search works
            </Button>
          }
        >
          <Bullets items={RAG_SOURCES} />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            Every answer cites a <code>path:line</code> you can open and check.
          </Typography>
        </Summary>
      </Box>

    </Box>
  );
}

// Every skill, one category card per row. Used on "The skills" page.
export function SkillCards() {
  return (
    <Box sx={{ my: 3 }}>
      <Stack gap={2}>
        {skillGroups.map((g) => (
          <Box key={g.title} id={skillAnchor(g.title)} sx={{ scrollMarginTop: 88, border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden', bgcolor: 'background.paper' }}>
            <Typography
              variant="overline"
              color="text.secondary"
              component="div"
              sx={{ px: 1.75, py: 0.75, borderBottom: 1, borderColor: 'divider', bgcolor: (t) => alpha(t.palette.text.primary, 0.03) }}
            >
              {g.title} · {g.skills.length}
            </Typography>
            <Stack component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }} divider={<Box component="li" aria-hidden sx={{ borderTop: 1, borderColor: 'divider' }} />}>
              {g.skills.map((s) => (
                <Box
                  component="li"
                  key={s.name}
                  sx={{ px: 1.75, py: 1.1, display: 'grid', gap: { xs: 0.25, sm: 2 }, gridTemplateColumns: { xs: '1fr', sm: '230px minmax(0, 1fr)' } }}
                >
                  <Typography sx={{ fontFamily: fonts.mono, fontSize: '0.8rem', fontWeight: 500, color: 'primary.main', overflowWrap: 'anywhere', pt: '2px' }}>{s.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.55 }}>
                    {s.desc}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
