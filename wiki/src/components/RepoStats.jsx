import { useEffect, useState } from 'react';
import { Link, Stack } from '@mui/material';
import StarBorderRoundedIcon from '@mui/icons-material/StarBorderRounded';
import ForkRightRoundedIcon from '@mui/icons-material/ForkRightRounded';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import { fonts } from '../theme.js';

// Live star, fork and watcher counts from the public GitHub API.
// Unauthenticated calls are limited per visitor, so one result is kept for the browser session.
// If the API can't be reached, the footer simply shows no counts.

const API = 'https://api.github.com/repos/DayZ-n-Chill/Agentic-Z';
const CACHE_KEY = 'agentic-z-repo-stats';

function readCache() {
  try {
    return JSON.parse(sessionStorage.getItem(CACHE_KEY));
  } catch {
    return null;
  }
}

const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });

export default function RepoStats({ repoUrl }) {
  const [stats, setStats] = useState(readCache);

  useEffect(() => {
    if (stats) return;
    let live = true;
    fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        const next = { stars: d.stargazers_count, forks: d.forks_count, watchers: d.subscribers_count };
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify(next));
        } catch {
          // Storage blocked: the counts still show for this page view.
        }
        if (live) setStats(next);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [stats]);

  if (!stats) return null;

  const items = [
    { icon: StarBorderRoundedIcon, n: stats.stars, label: 'stars', href: `${repoUrl}/stargazers` },
    { icon: ForkRightRoundedIcon, n: stats.forks, label: 'forks', href: `${repoUrl}/forks` },
    { icon: VisibilityOutlinedIcon, n: stats.watchers, label: 'watching', href: `${repoUrl}/watchers` },
  ].filter((i) => Number.isFinite(i.n));

  return (
    <Stack direction="row" gap={2} alignItems="center">
      {items.map(({ icon: Icon, n, label, href }) => (
        <Link
          key={label}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          underline="none"
          title={`${n.toLocaleString('en')} ${label} on GitHub`}
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.5,
            color: 'text.secondary',
            fontFamily: fonts.mono,
            fontSize: '0.78rem',
            '&:hover': { color: 'primary.main' },
          }}
        >
          <Icon sx={{ fontSize: 16 }} />
          {compact.format(n)}
          <span>{label}</span>
        </Link>
      ))}
    </Stack>
  );
}
