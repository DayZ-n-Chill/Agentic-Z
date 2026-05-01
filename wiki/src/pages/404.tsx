import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function NotFound(): ReactNode {
  return (
    <Layout title="404 — Off the Map" description="You wandered too far from the spawn.">
      <main
        style={{
          minHeight: 'calc(100vh - 60px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background:
            'radial-gradient(ellipse at top, rgba(160, 66, 31, 0.15) 0%, transparent 60%), linear-gradient(180deg, #1a1a14 0%, #0f0f0a 100%)',
          padding: '4rem 1.5rem',
          textAlign: 'center',
        }}>
        <div style={{maxWidth: 640}}>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.78rem',
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: '#cc6e2f',
              marginBottom: '1rem',
            }}>
            // signal lost
          </div>
          <h1
            style={{
              fontFamily: 'Oswald, sans-serif',
              fontSize: 'clamp(3.5rem, 9vw, 7rem)',
              fontWeight: 700,
              letterSpacing: '0.06em',
              color: '#e8e4d4',
              margin: '0 0 0.5rem',
              textTransform: 'uppercase',
              textShadow:
                '0 0 24px rgba(160, 66, 31, 0.35), 0 2px 0 rgba(0, 0, 0, 0.6)',
            }}>
            4<span style={{color: '#cc6e2f'}}>0</span>4
          </h1>
          <p
            style={{
              fontFamily: 'Oswald, sans-serif',
              fontSize: 'clamp(1.1rem, 2vw, 1.5rem)',
              color: '#c9c4a8',
              letterSpacing: '0.04em',
              marginBottom: '2rem',
            }}>
            You wandered too far from the spawn.
          </p>
          <p
            style={{
              color: '#c9c4a8',
              fontSize: '1.05rem',
              lineHeight: 1.6,
              marginBottom: '2.5rem',
            }}>
            The page you were looking for is either out of bounds, despawned, or never existed in the first place. Head back to base camp and try a fresh route.
          </p>
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              justifyContent: 'center',
              flexWrap: 'wrap',
            }}>
            <Link
              to="/"
              style={{
                fontFamily: 'Oswald, sans-serif',
                fontSize: '0.95rem',
                fontWeight: 700,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                padding: '0.9rem 1.8rem',
                background: '#8b3a1f',
                border: '2px solid #a0421f',
                color: '#fff',
                textDecoration: 'none',
              }}>
              Back to Base →
            </Link>
            <Link
              to="/docs/intro"
              style={{
                fontFamily: 'Oswald, sans-serif',
                fontSize: '0.95rem',
                fontWeight: 600,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                padding: '0.9rem 1.8rem',
                background: 'transparent',
                border: '2px solid #c9c4a8',
                color: '#c9c4a8',
                textDecoration: 'none',
              }}>
              Read the Manual
            </Link>
          </div>
        </div>
      </main>
    </Layout>
  );
}
