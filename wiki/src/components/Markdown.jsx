import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Alert,
  Box,
  IconButton,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import SchemaOutlinedIcon from '@mui/icons-material/SchemaOutlined';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import { slugify, anchorIndex } from '../content.js';
import { fonts } from '../theme.js';
import Includes, { SkillCards } from './Includes.jsx';
import Requirements from './Requirements.jsx';
import Diagram from './Diagram.jsx';
import TableCards from './TableCards.jsx';
import FileTree from './FileTree.jsx';
import { diagrams } from '../diagrams.js';

function textOf(children) {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map(textOf).join('');
  if (children?.props) return textOf(children.props.children);
  return '';
}

function codeLabel(text) {
  const lines = text.split('\n').filter(Boolean);
  if (lines.length && lines.every((l) => l.startsWith('/'))) return 'Claude Code';
  if (lines.some((l) => /^(git|cd|python|py|npm|claude)\b/.test(l))) return 'Terminal';
  return '';
}

function CodeBlock({ text, children }) {
  const [copied, setCopied] = useState(false);
  const copy = async (e) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard refused: select the text so the reader can copy it by hand.
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(e.currentTarget.closest('[data-code]').querySelector('pre'));
      sel.removeAllRanges();
      sel.addRange(range);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  const label = codeLabel(text);
  return (
    <Box
      data-code
      sx={{
        my: 2,
        borderRadius: 1,
        border: 1,
        borderColor: 'divider',
        overflow: 'hidden',
        bgcolor: (t) => (t.palette.mode === 'dark' ? '#0A0E10' : '#1B2328'),
        color: '#E4E8E6',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pl: 2,
          pr: 0.5,
          py: 0.25,
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <Typography
          component="span"
          sx={{ fontFamily: fonts.mono, fontSize: '0.68rem', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(228,232,230,0.55)' }}
        >
          {label}
        </Typography>
        <Tooltip title={copied ? 'Copied' : 'Copy'} placement="left">
          <IconButton
            size="small"
            onClick={copy}
            aria-label="Copy to clipboard"
            sx={{ color: copied ? '#6FBF73' : 'rgba(228,232,230,0.7)', '&:hover': { color: '#E2A33B' } }}
          >
            {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
      </Box>
      <Box
        component="pre"
        sx={{ fontFamily: fonts.mono, fontSize: '0.84rem', lineHeight: 1.65, m: 0, px: 2, py: 1.5, overflowX: 'auto' }}
      >
        {children}
      </Box>
    </Box>
  );
}

export default function Markdown({ source, onNavigate }) {
  const components = {
    h3: ({ children }) => (
      <Typography variant="h3" id={slugify(textOf(children))} sx={{ mt: 5, mb: 1.5, scrollMarginTop: 88 }}>
        {children}
      </Typography>
    ),
    h4: ({ children }) => (
      <Typography variant="h4" id={slugify(textOf(children))} sx={{ mt: 3.5, mb: 1, scrollMarginTop: 88 }}>
        {children}
      </Typography>
    ),
    p: ({ node, children }) =>
      node?.children?.length === 1 && node.children[0].tagName === 'img' ? (
        <>{children}</>
      ) : (
      <Typography variant="body1" component="p" sx={{ my: 1.5 }}>
        {children}
      </Typography>
    ),
    a: ({ href = '', children }) => {
      if (href.startsWith('#')) {
        const target = anchorIndex[href.slice(1)];
        return (
          <Link
            href={target ? `#${target.page}` : href}
            onClick={(e) => {
              if (!target) return;
              e.preventDefault();
              onNavigate(target.page, target.anchor);
            }}
          >
            {children}
          </Link>
        );
      }
      return (
        <Link href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </Link>
      );
    },
    // Lists: numbered steps get a badge each; bullets get room to breathe.
    ul: ({ children }) => (
      <Box
        component="ul"
        sx={{
          listStyle: 'none',
          p: 0,
          my: 2,
          display: 'grid',
          gap: 1.25,
          '& > li': { position: 'relative', pl: 2.5, lineHeight: 1.7 },
          '& > li::before': {
            content: '""',
            position: 'absolute',
            left: 4,
            top: '0.72em',
            width: 6,
            height: 6,
            borderRadius: '1px',
            bgcolor: 'primary.main',
          },
        }}
      >
        {children}
      </Box>
    ),
    ol: ({ children, start }) => (
      <Box
        component="ol"
        start={start}
        sx={{
          listStyle: 'none',
          p: 0,
          my: 2.5,
          display: 'grid',
          gap: 1.5,
          counterReset: `step ${(start || 1) - 1}`,
          '& > li': { position: 'relative', pl: 5, minHeight: 28, lineHeight: 1.7, counterIncrement: 'step' },
          '& > li::before': {
            content: 'counter(step)',
            position: 'absolute',
            left: 0,
            top: 0,
            width: 28,
            height: 28,
            display: 'grid',
            placeItems: 'center',
            borderRadius: 1,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'background.paper',
            fontFamily: fonts.mono,
            fontSize: '0.78rem',
            fontWeight: 600,
            color: 'primary.main',
          },
        }}
      >
        {children}
      </Box>
    ),
    // A bullet that opens with a bold lead ("**A rule:** text") puts the lead on its own line.
    li: ({ children }) => {
      const items = Array.isArray(children) ? children : [children];
      const first = items[0];
      const lead = first?.type === 'strong' || first?.props?.node?.tagName === 'strong';
      if (!lead) return <li>{children}</li>;
      const text = textOf(first.props.children).replace(/:\s*$/, '');
      return (
        <li>
          <Box component="strong" sx={{ display: 'block', fontWeight: 600, color: 'text.primary' }}>
            {text}
          </Box>
          <Box component="span" sx={{ color: 'text.secondary' }}>
            {items.slice(1).map((c, i) => (i === 0 && typeof c === 'string' ? c.replace(/^\s+(\S)/, (_, ch) => ch.toUpperCase()) : c))}
          </Box>
        </li>
      );
    },
    blockquote: ({ children }) => (
      <Box
        component="blockquote"
        sx={{
          m: 0,
          my: 2,
          px: 2,
          py: 0.5,
          borderLeft: 3,
          borderColor: 'primary.main',
          bgcolor: (t) => alpha(t.palette.primary.main, 0.06),
          borderRadius: '0 4px 4px 0',
        }}
      >
        {children}
      </Box>
    ),
    code: ({ className, children }) => {
      const isBlock = /language-/.test(className || '') || String(children).includes('\n');
      if (isBlock) return <code className={className}>{children}</code>;
      return (
        <Box
          component="code"
          sx={{
            fontFamily: fonts.mono,
            fontSize: '0.84em',
            px: 0.6,
            py: 0.15,
            borderRadius: 0.75,
            bgcolor: (t) => alpha(t.palette.text.primary, 0.07),
            border: 1,
            borderColor: 'divider',
            overflowWrap: 'anywhere',
          }}
        >
          {children}
        </Box>
      );
    },
    pre: ({ children }) => <CodeBlock text={textOf(children).replace(/\n$/, '')}>{children}</CodeBlock>,
    // Diagram SVGs from the source docs aren't in the repo yet; show a labelled slot instead.
    img: ({ src = '', alt }) => {
      const spec = diagrams[src.split('/').pop()];
      if (spec) return <Diagram spec={spec} title={alt && alt !== 'Diagram' ? alt : ''} />;
      return (
      <Box
        component="span"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          my: 2.5,
          px: 2,
          py: 3,
          border: 1,
          borderStyle: 'dashed',
          borderColor: 'divider',
          borderRadius: 1,
          color: 'text.secondary',
        }}
      >
        <SchemaOutlinedIcon fontSize="small" />
        <Typography component="span" variant="body2">
          {alt || 'Diagram'} (diagram slot)
        </Typography>
      </Box>
      );
    },
    table: ({ children }) => (
      <TableContainer
        sx={{ my: 2.5, border: 1, borderColor: 'divider', borderRadius: 1, bgcolor: 'background.paper' }}
      >
        <Table size="small">{children}</Table>
      </TableContainer>
    ),
    thead: ({ children }) => <TableHead>{children}</TableHead>,
    tbody: ({ children }) => (
      <TableBody sx={{ '& tr:last-of-type td': { borderBottom: 0 } }}>{children}</TableBody>
    ),
    tr: ({ children }) => <TableRow hover>{children}</TableRow>,
    th: ({ children }) => <TableCell>{children}</TableCell>,
    td: ({ children }) => <TableCell sx={{ minWidth: 120 }}>{children}</TableCell>,
    hr: () => <Box component="hr" sx={{ border: 0, borderTop: 1, borderColor: 'divider', my: 4 }} />,
  };

  const render = (md, key) => (
    <ReactMarkdown key={key} remarkPlugins={[remarkGfm]} components={components}>
      {md}
    </ReactMarkdown>
  );

  // GitHub-style callouts: "> [!NOTE]", "> [!TIP]", "> [!WARNING]" become MUI alerts.
  const parts = source.split(/^(> \[!(?:NOTE|TIP|WARNING)\]\n(?:>.*(?:\n|$))+|:::includes$|:::skills$|:::requirements$|:::tree [^\n]*\n[\s\S]*?\n:::$|(?:^\|.*\|[ \t]*(?:\n|$))+)/m);
  return parts.map((part, i) => {
    if (/^\|.*\|\s*\n\|\s*:?-{3,}/.test(part))
      return <TableCards key={i} source={part} renderInline={(md) => render(md, 'c')} />;
    if (part.startsWith(':::tree ')) return <FileTree key={i} source={part} />;
    if (part === ':::includes') return <Includes key={i} onNavigate={onNavigate} />;
    if (part === ':::skills') return <SkillCards key={i} />;
    if (part === ':::requirements') return <Requirements key={i} renderInline={(md) => render(md, 'r')} />;
    const m = part.match(/^> \[!(NOTE|TIP|WARNING)\]\n/);
    if (!m) return part.trim() ? render(part, i) : null;
    const body = part
      .slice(m[0].length)
      .split('\n')
      .map((l) => l.replace(/^> ?/, ''))
      .join('\n');
    const severity = { NOTE: 'info', TIP: 'success', WARNING: 'warning' }[m[1]];
    return (
      <Alert
        key={i}
        severity={severity}
        variant="outlined"
        sx={{ my: 2.5, '& .MuiAlert-message': { py: 0.5 }, '& p': { my: 0 } }}
      >
        {render(body, 'b')}
      </Alert>
    );
  });
}
