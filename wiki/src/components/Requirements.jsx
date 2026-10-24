import { Box, Chip, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import DesktopWindowsOutlinedIcon from '@mui/icons-material/DesktopWindowsOutlined';
import SportsEsportsOutlinedIcon from '@mui/icons-material/SportsEsportsOutlined';
import HandymanOutlinedIcon from '@mui/icons-material/HandymanOutlined';
import DnsOutlinedIcon from '@mui/icons-material/DnsOutlined';
import StorageOutlinedIcon from '@mui/icons-material/StorageOutlined';
import CodeOutlinedIcon from '@mui/icons-material/CodeOutlined';
import TerminalOutlinedIcon from '@mui/icons-material/TerminalOutlined';
import { requirements } from '../content.js';
import { fonts } from '../theme.js';

function iconFor(name) {
  if (/^Windows/.test(name)) return DesktopWindowsOutlinedIcon;
  if (/^DayZ Tools/.test(name)) return HandymanOutlinedIcon;
  if (/^DayZ Server/.test(name)) return DnsOutlinedIcon;
  if (/^DayZ/.test(name)) return SportsEsportsOutlinedIcon;
  if (/^P:/.test(name)) return StorageOutlinedIcon;
  if (/^Python/.test(name)) return CodeOutlinedIcon;
  return TerminalOutlinedIcon;
}

// "DayZ Tools (Steam, free)" -> title "DayZ Tools", tags ["Steam", "free"]
function splitName(name) {
  const m = name.match(/^(.*?)\s*\((.+)\)$/);
  if (!m) return { title: name, tags: [] };
  const inner = m[2];
  const tags = inner.startsWith('or ') ? [inner] : inner.split(/,\s*/);
  return { title: m[1], tags };
}

export default function Requirements({ renderInline }) {
  return (
    <Box component="ul" sx={{ listStyle: 'none', p: 0, my: 3, borderTop: 1, borderColor: 'divider' }}>
      {requirements.map((r) => {
        const Icon = iconFor(r.name);
        const { title, tags } = splitName(r.name);
        return (
          <Box component="li" key={r.name} sx={{ display: 'flex', gap: 2, py: 1.75, borderBottom: 1, borderColor: 'divider' }}>
            <Box
              sx={(t) => ({
                width: 36,
                height: 36,
                flexShrink: 0,
                display: 'grid',
                placeItems: 'center',
                borderRadius: 1,
                color: t.palette.primary.main,
                bgcolor: alpha(t.palette.primary.main, 0.12),
              })}
            >
              <Icon fontSize="small" />
            </Box>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Stack direction="row" alignItems="center" gap={0.75} sx={{ flexWrap: 'wrap', mb: 0.25 }}>
                <Typography sx={{ fontFamily: fonts.display, fontWeight: 600, fontSize: '1rem', lineHeight: 1.3 }}>{title}</Typography>
                {tags.map((tag) => (
                  <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem', fontFamily: fonts.mono }} />
                ))}
              </Stack>
              <Typography
                variant="body2"
                color="text.secondary"
                component="div"
                sx={{ lineHeight: 1.55, '& p': { m: 0, fontSize: 'inherit', lineHeight: 'inherit' } }}
              >
                {renderInline(r.purpose)}
              </Typography>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
