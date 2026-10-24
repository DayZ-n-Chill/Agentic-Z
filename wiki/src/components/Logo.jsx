import { Box } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import logoDark from '../assets/logo-dark.png';
import logoLight from '../assets/logo-light.png';

// The Agentic-Z mark. The light-mode file darkens the grey "A" so it reads on a pale background.
// `size` is the height in pixels; the width follows the mark's proportions. `sx` overrides either.
export default function Logo({ size = 32, sx }) {
  const theme = useTheme();
  return (
    <Box
      component="img"
      src={theme.palette.mode === 'dark' ? logoDark : logoLight}
      alt="Agentic-Z"
      sx={{ height: size, width: 'auto', flexShrink: 0, display: 'block', ...sx }}
    />
  );
}
