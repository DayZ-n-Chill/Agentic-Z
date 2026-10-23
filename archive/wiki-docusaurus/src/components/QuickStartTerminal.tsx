import type {ReactNode} from 'react';
import ModNameCycle from './ModNameCycle';
import styles from './QuickStartTerminal.module.css';

interface Props {
  /** "center" (default) keeps the homepage look. "left" pins it to the
   *  left edge of the column for use inside doc pages. */
  align?: 'center' | 'left';
}

export default function QuickStartTerminal({align = 'center'}: Props): ReactNode {
  const alignClass = align === 'left' ? styles.terminalWrapLeft : '';
  return (
    <div className={`${styles.terminalWrap} ${alignClass}`}>
      <div className={styles.terminalBar}>~ // claude code — agentic-z install</div>
      <div className={styles.terminalBody}>
        <div>
          <span className={styles.terminalComment}>
            # 1. Add the marketplace + install the plugin
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>&gt;</span>
          <span className={styles.terminalCommand}>
            /plugin marketplace add DayZ-n-Chill/Agentic-Z
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>&gt;</span>
          <span className={styles.terminalCommand}>
            /plugin install agentic-z@dayz-n-chill
          </span>
        </div>
        <div>&nbsp;</div>
        <div>
          <span className={styles.terminalComment}>
            # 2. Run the wizard — env check, scaffold, build, launch
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>&gt;</span>
          <span className={styles.terminalCommand}>/dayz-init</span>
        </div>
        <div>&nbsp;</div>
        <div>
          <span className={styles.terminalComment}>
            # That's it. Wizard scaffolds <ModNameCycle />, builds the PBO, and launches diag.
          </span>
        </div>
      </div>
    </div>
  );
}
