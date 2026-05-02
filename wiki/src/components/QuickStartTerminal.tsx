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
      <div className={styles.terminalBar}>~ // bash — agentic-z bootstrap</div>
      <div className={styles.terminalBody}>
        <div>
          <span className={styles.terminalComment}>
            # 1. Clone and link skills into every agent CLI
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>$</span>
          <span className={styles.terminalCommand}>
            git clone &lt;agentic-z&gt; my-mod &amp;&amp; cd my-mod
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>$</span>
          <span className={styles.terminalCommand}>
            python .claude/skills/sync-skills/sync.py
          </span>
        </div>
        <div>&nbsp;</div>
        <div>
          <span className={styles.terminalComment}>
            # 2. Verify DayZ environment (P:\, DayZ Tools, vanilla data)
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>&gt;</span>
          <span className={styles.terminalCommand}>/dayz-preflight</span>
        </div>
        <div>&nbsp;</div>
        <div>
          <span className={styles.terminalComment}>
            # 3. Scaffold a new mod
          </span>
        </div>
        <div>
          <span className={styles.terminalPrompt}>&gt;</span>
          <span className={styles.terminalCommand}>
            /dayz-new-mod <ModNameCycle />
          </span>
        </div>
      </div>
    </div>
  );
}
