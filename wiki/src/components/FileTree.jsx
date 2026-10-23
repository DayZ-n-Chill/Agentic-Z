import { Box, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined';
import { fonts } from '../theme.js';

// A static folder tree from a ":::tree <root>" block. One entry per line, two spaces per level:
//   name\ | note | local
// A trailing "\" marks a folder. "local" marks something created on your PC that is not in git.
// Each level is sorted like a file explorer, with dot entries first: dot folders, dot files, folders, files.

function parse(lines) {
  const root = { children: [] };
  const stack = [{ depth: -1, node: root }];
  for (const raw of lines) {
    if (!raw.trim()) continue;
    const depth = raw.match(/^ */)[0].length / 2;
    const [name, note = '', flag = ''] = raw.trim().split(/\s*\|\s*/);
    const node = { name: name.replace(/\\$/, ''), folder: name.endsWith('\\'), note, local: flag === 'local', children: [] };
    while (stack[stack.length - 1].depth >= depth) stack.pop();
    stack[stack.length - 1].node.children.push(node);
    stack.push({ depth, node });
  }
  return root.children;
}

const rank = (n) => (n.name.startsWith('.') ? 0 : 2) + (n.folder ? 0 : 1);
const sortTree = (nodes) =>
  [...nodes]
    .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, 'en', { sensitivity: 'base' }))
    .map((n) => ({ ...n, children: sortTree(n.children) }));

function Row({ node, depth }) {
  const Icon = node.folder ? FolderOutlinedIcon : InsertDriveFileOutlinedIcon;
  return (
    <>
      <Box
        component="li"
        sx={{
          display: 'grid',
          // Fixed name column so every note lines up, whatever the depth.
          gridTemplateColumns: { xs: '1fr', sm: '340px minmax(0, 1fr)' },
          columnGap: 2,
          alignItems: 'center',
          py: 0.4,
          pl: '12px',
          pr: 1.5,
          position: 'relative',
          // Indent guides, one per level.
          backgroundImage: (t) =>
            depth
              ? `repeating-linear-gradient(to right, ${t.palette.divider} 0 1px, transparent 1px 20px)`
              : 'none',
          backgroundSize: `${depth * 20}px 100%`,
          backgroundPosition: '20px 0',
          backgroundRepeat: 'no-repeat',
          '&:hover': { bgcolor: (t) => alpha(t.palette.text.primary, 0.03) },
        }}
      >
        <Stack direction="row" alignItems="center" gap={0.75} sx={{ minWidth: 0, pl: `${depth * 20}px` }}>
          <Icon sx={{ fontSize: 16, color: node.folder ? 'primary.main' : 'text.secondary', flexShrink: 0 }} />
          <Typography
            component="span"
            sx={{
              fontFamily: fonts.mono,
              fontSize: '0.8rem',
              fontWeight: node.folder ? 500 : 400,
              color: node.folder ? 'text.primary' : 'text.secondary',
              whiteSpace: 'nowrap',
              fontVariantLigatures: 'none',
            }}
          >
            {node.name}
            {node.folder ? '\\' : ''}
          </Typography>
          {node.local && (
            <Typography
              component="span"
              sx={{
                fontFamily: fonts.mono,
                fontSize: '0.6rem',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'text.secondary',
                border: 1,
                borderColor: 'divider',
                borderRadius: 0.5,
                px: 0.5,
                lineHeight: 1.5,
              }}
            >
              local
            </Typography>
          )}
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.82rem', pl: { xs: `${depth * 20 + 22}px`, sm: 0 } }}>
          {node.note}
        </Typography>
      </Box>
      {node.children.map((c) => (
        <Row key={c.name} node={c} depth={depth + 1} />
      ))}
    </>
  );
}

export default function FileTree({ source }) {
  const [head, ...lines] = source.replace(/\n:::$/, '').split('\n');
  const rootPath = head.replace(/^:::tree\s*/, '');
  const nodes = sortTree(parse(lines));
  return (
    <Box sx={{ my: 2.5, border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden', bgcolor: 'background.paper' }}>
      <Stack
        direction="row"
        alignItems="center"
        gap={1}
        sx={{ px: 1.5, py: 0.9, borderBottom: 1, borderColor: 'divider', bgcolor: (t) => alpha(t.palette.text.primary, 0.03) }}
      >
        <FolderOutlinedIcon sx={{ fontSize: 16, color: 'primary.main' }} />
        <Typography sx={{ fontFamily: fonts.mono, fontSize: '0.8rem', fontWeight: 600 }}>{rootPath}</Typography>
      </Stack>
      <Box component="ul" sx={{ listStyle: 'none', m: 0, py: 0.75, px: 0, overflowX: 'auto' }}>
        {nodes.map((n) => (
          <Row key={n.name} node={n} depth={0} />
        ))}
      </Box>
    </Box>
  );
}
