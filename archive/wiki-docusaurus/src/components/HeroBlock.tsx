import type {ReactNode} from 'react';
import styles from './HeroBlock.module.css';

interface HeroBlockProps {
  /** Optional override — path to an actual rendered illustration. */
  src?: string;
  alt?: string;
  /** Tagline / subhead under the title. */
  children?: ReactNode;
}

/**
 * Page hero with a placeholder 3D-style block on the right.
 *
 *   <HeroBlock>
 *     # Page Title <Pill variant="rust">Beta</Pill>
 *     Tagline goes here.
 *   </HeroBlock>
 *
 * Drop a real image into `static/img/heroes/<name>.png` and pass `src="/img/heroes/<name>.png"`
 * to replace the placeholder.
 */
export default function HeroBlock({src, alt = '', children}: HeroBlockProps): ReactNode {
  return (
    <div className={styles.hero}>
      <div className={styles.heroContent}>{children}</div>
      <div className={styles.heroIllustration}>
        {src ? (
          <img src={src} alt={alt} className={styles.heroImage} />
        ) : (
          <div className={styles.placeholder} aria-hidden="true">
            <div className={styles.cube}>
              <div className={`${styles.face} ${styles.top}`} />
              <div className={`${styles.face} ${styles.right}`} />
              <div className={`${styles.face} ${styles.front}`} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
