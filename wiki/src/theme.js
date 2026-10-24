import { createTheme, alpha } from '@mui/material/styles';

// Layout: fixed top bar, left nav drawer, reading column (~72ch), right "on this page" rail.
// Palette: field-slate neutrals with a signal-amber accent. Swap `brand` once the logo colors are final.
export const brand = {
  amber: '#E2A33B',
  amberDeep: '#A8670F',
  slate: '#0F1417',
  slatePaper: '#151C20',
  slateLine: '#26323A',
  bone: '#F4F5F1',
};

export const fonts = {
  display: '"Chakra Petch", "Segoe UI", system-ui, sans-serif',
  body: '"IBM Plex Sans", "Segoe UI", system-ui, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, "Cascadia Code", Consolas, monospace',
};

export function makeTheme(mode) {
  const dark = mode === 'dark';
  const primary = dark ? brand.amber : brand.amberDeep;
  return createTheme({
    palette: {
      mode,
      primary: { main: primary, contrastText: dark ? '#14100A' : '#FFFFFF' },
      secondary: { main: dark ? '#7FA7A0' : '#3E6B64' },
      background: {
        default: dark ? brand.slate : brand.bone,
        paper: dark ? brand.slatePaper : '#FFFFFF',
      },
      text: {
        primary: dark ? '#E4E8E6' : '#1A2328',
        secondary: dark ? '#9AA6A4' : '#55626A',
      },
      divider: dark ? brand.slateLine : '#DDE1DC',
      success: { main: dark ? '#6FBF73' : '#2E7D32' },
    },
    shape: { borderRadius: 6 },
    typography: {
      fontFamily: fonts.body,
      fontSize: 15,
      h1: { fontFamily: fonts.display, fontWeight: 700, fontSize: '2.4rem', letterSpacing: '-0.01em', lineHeight: 1.15 },
      h2: { fontFamily: fonts.display, fontWeight: 600, fontSize: '1.55rem', lineHeight: 1.25 },
      h3: { fontFamily: fonts.display, fontWeight: 600, fontSize: '1.2rem', lineHeight: 1.3 },
      h4: { fontFamily: fonts.display, fontWeight: 600, fontSize: '1.02rem' },
      overline: { fontFamily: fonts.mono, fontWeight: 500, letterSpacing: '0.12em', fontSize: '0.7rem' },
      body1: { lineHeight: 1.7 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: { WebkitFontSmoothing: 'antialiased' },
          // Scrollbars in the theme's colors instead of the browser default.
          '*': {
            scrollbarWidth: 'thin',
            scrollbarColor: `${alpha(dark ? '#E4E8E6' : '#1A2328', 0.22)} transparent`,
          },
          '*::-webkit-scrollbar': { width: 10, height: 10 },
          '*::-webkit-scrollbar-track': { background: 'transparent' },
          '*::-webkit-scrollbar-thumb': {
            backgroundColor: alpha(dark ? '#E4E8E6' : '#1A2328', 0.22),
            borderRadius: 8,
            border: '3px solid transparent',
            backgroundClip: 'content-box',
          },
          '*::-webkit-scrollbar-thumb:hover': { backgroundColor: alpha(primary, 0.7) },
          '*::-webkit-scrollbar-corner': { background: 'transparent' },
          'h1,h2,h3,h4': { textWrap: 'balance' },
          '::selection': { background: alpha(primary, 0.3) },
          '@media (prefers-reduced-motion: reduce)': {
            '*': { transition: 'none !important', scrollBehavior: 'auto !important' },
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: alpha(theme.palette.background.default, 0.88),
            backdropFilter: 'blur(10px)',
            color: theme.palette.text.primary,
            borderBottom: `1px solid ${theme.palette.divider}`,
            boxShadow: 'none',
          }),
        },
      },
      MuiDrawer: {
        styleOverrides: { paper: ({ theme }) => ({ backgroundColor: theme.palette.background.default }) },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: 4,
            paddingTop: 4,
            paddingBottom: 4,
            '&.Mui-selected': {
              backgroundColor: alpha(theme.palette.primary.main, 0.12),
              color: theme.palette.primary.main,
              '&:hover': { backgroundColor: alpha(theme.palette.primary.main, 0.18) },
            },
          }),
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: { fontSize: '0.875rem', lineHeight: 1.55, verticalAlign: 'top' },
          head: ({ theme }) => ({
            fontFamily: fonts.mono,
            fontSize: '0.72rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: theme.palette.text.secondary,
            whiteSpace: 'nowrap',
          }),
        },
      },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
    },
  });
}
