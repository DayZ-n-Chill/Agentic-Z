import type {ReactNode} from 'react';
import CodeBlock from '@theme/CodeBlock';
import styles from './Section.module.css';

interface SectionProps {
  children: ReactNode;
  code?: string;
  language?: string;
  codeTitle?: string;
}

/**
 * Two-column layout: prose on the left, optional code panel docked on the right.
 *
 *   <Section code="git clone ..." language="bash" codeTitle="install">
 *     ## Heading
 *     Some prose here.
 *   </Section>
 *
 * Stacks vertically on narrow viewports.
 */
export default function Section({
  children,
  code,
  language = 'bash',
  codeTitle,
}: SectionProps): ReactNode {
  return (
    <div className={styles.section}>
      <div className={styles.prose}>{children}</div>
      {code && (
        <div className={styles.codeColumn}>
          <div className={styles.codeSticky}>
            <CodeBlock language={language} title={codeTitle}>
              {code.trim()}
            </CodeBlock>
          </div>
        </div>
      )}
    </div>
  );
}
