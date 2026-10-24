import { Box } from '@mui/material';

// Placeholder mark until the real Agentic-Z logo file is dropped in.
// To swap: put the file at src/assets/logo.svg (or .png) and render <img src={logoUrl} /> here.
export default function Logo({ size = 32 }) {
  return (
    <Box
      component="svg"
      viewBox="0 0 64 64"
      sx={{ width: size, height: size, flexShrink: 0, color: 'primary.main' }}
      aria-label="Agentic-Z"
      role="img"
    >
      <rect x="2" y="2" width="60" height="60" rx="10" fill="none" stroke="currentColor" strokeWidth="3" />
      <path d="M18 19h28L22 45h24" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="square" />
      <circle cx="50" cy="14" r="3.5" fill="currentColor" />
    </Box>
  );
}
