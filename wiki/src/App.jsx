import { useEffect, useMemo, useState, useCallback } from 'react';
import {
  AppBar,
  Autocomplete,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardActionArea,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  InputAdornment,
  Link,
  List,
  ListItemButton,
  ListItemText,
  ListSubheader,
  Stack,
  TextField,
  ThemeProvider,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import GitHubIcon from '@mui/icons-material/GitHub';
import ForumOutlinedIcon from '@mui/icons-material/ForumOutlined';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import RocketLaunchOutlinedIcon from '@mui/icons-material/RocketLaunchOutlined';
import GroupsOutlinedIcon from '@mui/icons-material/GroupsOutlined';
import { groups, pages, intro, searchIndex } from './content.js';
import { makeTheme, fonts } from './theme.js';
import Logo from './components/Logo.jsx';
import Markdown from './components/Markdown.jsx';
import RepoStats from './components/RepoStats.jsx';
import HeroShader from './components/HeroShader.jsx';

const DRAWER = 280;
const REPO = 'https://github.com/DayZ-n-Chill/Agentic-Z';
const DISCORD = 'https://discord.gg/dayznchill';

function initialMode() {
  try {
    const saved = localStorage.getItem('azw-mode');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch {}
  const attr = document.documentElement.dataset.theme;
  if (attr === 'light' || attr === 'dark') return attr;
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function currentSlug() {
  const h = decodeURIComponent(window.location.hash.slice(1));
  return pages.some((p) => p.slug === h) ? h : '';
}

function NavList({ slug, onNavigate }) {
  return (
    <Box component="nav" aria-label="Wiki pages" sx={{ px: 1.5, pb: 4 }}>
      <List dense disablePadding>
        <ListItemButton selected={!slug} onClick={() => onNavigate('')} sx={{ mt: 1.5 }}>
          <ListItemText primary="Overview" primaryTypographyProps={{ fontWeight: 600 }} />
        </ListItemButton>
      </List>
      {groups.map((g) => (
        <List
          key={g.id}
          dense
          disablePadding
          subheader={
            <ListSubheader
              disableSticky
              sx={{
                bgcolor: 'transparent',
                fontFamily: fonts.mono,
                fontSize: '0.68rem',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                lineHeight: 1,
                pt: 3,
                pb: 1,
                px: 2,
              }}
            >
              {g.title}
            </ListSubheader>
          }
        >
          {g.pages.map((p) => (
            <ListItemButton key={p.slug} selected={p.slug === slug} onClick={() => onNavigate(p.slug)}>
              <ListItemText primary={p.title} primaryTypographyProps={{ fontSize: '0.875rem' }} />
            </ListItemButton>
          ))}
        </List>
      ))}
    </Box>
  );
}

function Search({ onNavigate }) {
  return (
    <Autocomplete
      size="small"
      options={searchIndex}
      groupBy={(o) => o.group}
      getOptionLabel={(o) => o.label}
      onChange={(_, v) => v && onNavigate(v.page, v.anchor)}
      blurOnSelect
      clearOnBlur
      sx={{ width: { xs: '100%', sm: 320 } }}
      renderInput={(params) => (
        <TextField
          {...params}
          id="wiki-search"
          placeholder="Search the wiki"
          InputProps={{
            ...params.InputProps,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      )}
    />
  );
}

function OnThisPage({ page }) {
  const [active, setActive] = useState('');
  useEffect(() => {
    if (!page?.headings.length) return;
    const els = page.headings.map((h) => document.getElementById(h.slug)).filter(Boolean);
    const io = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting);
        if (vis.length) setActive(vis[0].target.id);
      },
      { rootMargin: '-80px 0px -70% 0px' }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [page]);
  if (!page?.headings.length) return null;
  return (
    <Box sx={{ position: 'sticky', top: 88, alignSelf: 'start', maxHeight: 'calc(100vh - 112px)', overflowY: 'auto' }}>
      <Typography variant="overline" color="text.secondary">
        On this page
      </Typography>
      <Stack component="ul" sx={{ listStyle: 'none', p: 0, m: 0, mt: 1, borderLeft: 1, borderColor: 'divider' }}>
        {page.headings.map((h) => (
          <li key={h.slug}>
            <Link
              href={`#${page.slug}`}
              underline="none"
              onClick={(e) => {
                e.preventDefault();
                document.getElementById(h.slug)?.scrollIntoView({ behavior: 'smooth' });
              }}
              sx={{
                display: 'block',
                py: 0.5,
                pl: 1.5,
                ml: '-1px',
                fontSize: '0.8rem',
                borderLeft: 2,
                borderColor: active === h.slug ? 'primary.main' : 'transparent',
                color: active === h.slug ? 'primary.main' : 'text.secondary',
                '&:hover': { color: 'text.primary' },
              }}
            >
              {h.title}
            </Link>
          </li>
        ))}
      </Stack>
    </Box>
  );
}

function PagerCard({ page, dir, onNavigate }) {
  if (!page) return <Box sx={{ flex: 1 }} />;
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 0 }}>
      <CardActionArea onClick={() => onNavigate(page.slug)} sx={{ p: 2, textAlign: dir === 'next' ? 'right' : 'left' }}>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, justifyContent: dir === 'next' ? 'flex-end' : 'flex-start' }}>
          {dir === 'prev' && <ArrowBackIcon sx={{ fontSize: 14 }} />}
          {dir === 'prev' ? 'Previous' : 'Next'}
          {dir === 'next' && <ArrowForwardIcon sx={{ fontSize: 14 }} />}
        </Typography>
        <Typography fontWeight={600} color="primary">
          {page.title}
        </Typography>
      </CardActionArea>
    </Card>
  );
}

function PageView({ page, onNavigate }) {
  const i = pages.findIndex((p) => p.slug === page.slug);
  return (
    <Box component="article">
      <Breadcrumbs sx={{ mb: 2, fontSize: '0.8rem' }}>
        <Link component="button" underline="hover" color="text.secondary" onClick={() => onNavigate('')}>
          Wiki
        </Link>
        <Typography fontSize="inherit" color="text.secondary">
          {page.group}
        </Typography>
      </Breadcrumbs>
      <Typography variant="h1" sx={{ mb: 3 }}>
        {page.title}
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <Markdown source={page.body} onNavigate={onNavigate} />
      <Stack direction={{ xs: 'column', sm: 'row' }} gap={2} sx={{ mt: 8 }}>
        <PagerCard page={pages[i - 1]} dir="prev" onNavigate={onNavigate} />
        <PagerCard page={pages[i + 1]} dir="next" onNavigate={onNavigate} />
      </Stack>
    </Box>
  );
}

const STATS = [
  ['30', 'agents'],
  ['44', 'skills'],
  ['3', 'hooks'],
  ['163', 'parts graded A+', 'Every agent, skill and shared file, checked by independent reviewers'],
];

function Home({ onNavigate }) {
  return (
    <Box>
      <Box
        sx={{
          position: 'relative',
          overflow: 'hidden',
          border: 1,
          borderColor: 'divider',
          borderRadius: 2,
          p: { xs: 3, md: 5 },
          mb: 5,
          bgcolor: 'background.paper',
          backgroundImage: (t) =>
            `linear-gradient(${alpha(t.palette.text.primary, 0.045)} 1px, transparent 1px), linear-gradient(90deg, ${alpha(t.palette.text.primary, 0.045)} 1px, transparent 1px)`,
          backgroundSize: '28px 28px',
          '& > :not(canvas)': { position: 'relative', zIndex: 1 },
        }}
      >
        <HeroShader />
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={3} alignItems={{ sm: 'center' }}>
          <Logo size={96} />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="overline" color="primary">
              DayZ modding · Claude Code · Codex · Gemini
            </Typography>
            <Typography variant="h1" sx={{ fontSize: { xs: '2.2rem', md: '3rem' } }}>
              Agentic-Z Wiki
            </Typography>
          </Box>
        </Stack>
        <Typography sx={{ mt: 2.5, maxWidth: '62ch', fontSize: '1.05rem' }} color="text.secondary">
          {intro.replace('This guide explains', 'Everything about')}
        </Typography>
        <Stack direction="row" gap={1.5} sx={{ mt: 3, flexWrap: 'wrap' }}>
          <Button variant="contained" startIcon={<RocketLaunchOutlinedIcon />} onClick={() => onNavigate('install-and-first-setup')}>
            Install Agentic-Z
          </Button>
          <Button variant="outlined" startIcon={<GroupsOutlinedIcon />} onClick={() => onNavigate('the-mod-team')}>
            Meet the mod team
          </Button>
        </Stack>
        <Stack
          direction="row"
          sx={{ mt: 4, pt: 3, borderTop: 1, borderColor: 'divider', flexWrap: 'wrap', rowGap: 2, columnGap: { xs: 3, md: 5 } }}
        >
          {STATS.map(([n, label, note]) => (
            <Box key={label} sx={{ maxWidth: note ? '22ch' : undefined }}>
              <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: '1.8rem', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
                {n}
              </Typography>
              <Typography variant="overline" color="text.secondary">
                {label}
              </Typography>
              {note && (
                <Link
                  component="button"
                  underline="hover"
                  color="text.secondary"
                  onClick={() => onNavigate('how-the-grading-works')}
                  sx={{ display: 'block', textAlign: 'left', fontSize: '0.78rem', lineHeight: 1.45 }}
                >
                  {note}
                </Link>
              )}
            </Box>
          ))}
        </Stack>
      </Box>

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(3, minmax(0, 1fr))' } }}>
        {groups.map((g) => (
          <Card key={g.id} variant="outlined" sx={{ p: 2.5 }}>
            <Typography variant="overline" color="text.secondary">
              {g.pages.length} pages
            </Typography>
            <Typography variant="h3" sx={{ mb: 1.5 }}>
              {g.title}
            </Typography>
            <Stack component="ul" gap={0.75} sx={{ listStyle: 'none', p: 0, m: 0 }}>
              {g.pages.map((p) => (
                <li key={p.slug}>
                  <Link component="button" underline="hover" onClick={() => onNavigate(p.slug)} sx={{ textAlign: 'left', fontSize: '0.92rem' }}>
                    {p.title}
                  </Link>
                </li>
              ))}
            </Stack>
          </Card>
        ))}
      </Box>
    </Box>
  );
}

export default function App() {
  const [mode, setMode] = useState(initialMode);
  const [slug, setSlug] = useState(currentSlug);
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useMemo(() => makeTheme(mode), [mode]);
  const desktop = useMediaQuery(theme.breakpoints.up('md'));
  const wide = useMediaQuery(theme.breakpoints.up('lg'));
  const page = pages.find((p) => p.slug === slug);

  useEffect(() => {
    const onHash = () => setSlug(currentSlug());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    document.title = page ? `${page.title} · Agentic-Z Wiki` : 'Agentic-Z Wiki';
  }, [page]);

  const navigate = useCallback((next, anchor) => {
    setSlug(next);
    setMobileOpen(false);
    try {
      history.replaceState(null, '', next ? `#${next}` : window.location.pathname);
    } catch {}
    requestAnimationFrame(() => {
      const el = anchor && document.getElementById(anchor);
      if (el) el.scrollIntoView();
      else window.scrollTo(0, 0);
    });
  }, []);

  const toggleMode = () => {
    const next = mode === 'dark' ? 'light' : 'dark';
    setMode(next);
    try {
      localStorage.setItem('azw-mode', next);
    } catch {}
  };

  const drawer = <NavList slug={slug} onNavigate={navigate} />;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1, pt: 'env(safe-area-inset-top, 0px)' }}>
        <Toolbar sx={{ gap: 1.5, pl: 'max(16px, env(safe-area-inset-left, 0px))', pr: 'max(16px, env(safe-area-inset-right, 0px))' }}>
          {!desktop && (
            <IconButton edge="start" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
              <MenuIcon />
            </IconButton>
          )}
          <Link
            component="button"
            underline="none"
            color="inherit"
            onClick={() => navigate('')}
            sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}
          >
            <Logo size={26} />
            <Typography sx={{ fontFamily: fonts.display, fontWeight: 700, fontSize: '1.15rem', display: { xs: 'none', sm: 'block' } }}>
              Agentic-Z
            </Typography>
            <Typography
              variant="overline"
              sx={{ display: { xs: 'none', sm: 'block' }, px: 0.75, border: 1, borderColor: 'divider', borderRadius: 0.75, lineHeight: 1.6 }}
              color="text.secondary"
            >
              Wiki
            </Typography>
          </Link>
          <Box sx={{ flex: 1, display: { xs: 'none', sm: 'block' } }} />
          <Box sx={{ flex: { xs: 1, sm: 'none' }, minWidth: 0 }}>
            <Search onNavigate={navigate} />
          </Box>
          <Tooltip title="GitHub repository">
            <IconButton component="a" href={REPO} target="_blank" rel="noopener noreferrer" sx={{ display: { xs: 'none', sm: 'inline-flex' } }}>
              <GitHubIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Discord">
            <IconButton component="a" href={DISCORD} target="_blank" rel="noopener noreferrer" sx={{ display: { xs: 'none', sm: 'inline-flex' } }}>
              <ForumOutlinedIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={mode === 'dark' ? 'Light mode' : 'Dark mode'}>
            <IconButton onClick={toggleMode} aria-label="Toggle color mode">
              {mode === 'dark' ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: 'flex' }}>
        <Drawer
          variant={desktop ? 'permanent' : 'temporary'}
          open={desktop || mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            width: desktop ? DRAWER : 'auto',
            flexShrink: 0,
            '& .MuiDrawer-paper': { width: DRAWER, boxSizing: 'border-box', borderRight: 1, borderColor: 'divider' },
          }}
        >
          <Toolbar />
          {drawer}
        </Drawer>

        <Box
          component="main"
          sx={{
            flex: 1,
            minWidth: 0,
            pt: 'calc(64px + env(safe-area-inset-top, 0px))',
            pl: 'max(16px, env(safe-area-inset-left, 0px))',
            pr: 'max(16px, env(safe-area-inset-right, 0px))',
          }}
        >
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: page && wide ? 'minmax(0, 1fr) 220px' : 'minmax(0, 1fr)',
              gap: 6,
              maxWidth: page ? 1120 : 1200,
              mx: 'auto',
              py: { xs: 3, md: 5 },
              px: { md: 3 },
            }}
          >
            <Box sx={{ minWidth: 0, maxWidth: page ? '78ch' : 'none' }}>
              {page ? <PageView key={page.slug} page={page} onNavigate={navigate} /> : <Home onNavigate={navigate} />}
            </Box>
            {page && wide && <OnThisPage page={page} />}
          </Box>
          <Box
            component="footer"
            sx={{
              borderTop: 1,
              borderColor: 'divider',
              py: 3,
              px: { md: 3 },
              maxWidth: 1120,
              mx: 'auto',
              color: 'text.secondary',
              fontSize: '0.8rem',
              display: 'flex',
              flexWrap: 'wrap',
              gap: 2,
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span>Agentic-Z: a production-ready agent stack for DayZ modding.</span>
            <RepoStats repoUrl={REPO} />
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
