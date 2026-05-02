import type {ReactNode} from 'react';
import styles from './Pill.module.css';

type PillVariant = 'default' | 'rust' | 'sage' | 'bone' | 'olive';

interface PillProps {
  children: ReactNode;
  variant?: PillVariant;
}

export default function Pill({children, variant = 'default'}: PillProps): ReactNode {
  return <span className={`${styles.pill} ${styles[variant]}`}>{children}</span>;
}
