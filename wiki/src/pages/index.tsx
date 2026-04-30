import type {ReactNode} from 'react';
import {useEffect, useState} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import styles from './index.module.css';

const STATS = [
  {num: '12', label: 'Specialist Agents'},
  {num: '18', label: 'Slash Skills'},
  {num: '3', label: 'Agent CLIs'},
  {num: '1', label: 'Drive (P:\\)'},
];

const LAYERS = [
  {
    layer: 'L1',
    title: 'Default Rules',
    desc: 'Apply to every clone, every agent, every skill. Foundational guidelines that travel with the template.',
    path: 'CLAUDE.md / AGENTS.md / GEMINI.md',
  },
  {
    layer: 'L2',
    title: 'DayZ Conventions',
    desc: 'Domain-specific rules — P:\\ drive, $PBOPREFIX$, modded class anti-patterns, types.xml hygiene.',
    path: '.claude/skills/_shared/dayz-conventions.md',
  },
  {
    layer: 'L3',
    title: 'Agents & Skills',
    desc: 'The actual units of work. Specialist agents and slash-command skills the CLIs invoke.',
    path: '.claude/agents/ / .claude/skills/',
  },
];

const MOD_NAMES = [
  'MyTacticalVest',
  'BananaLauncher',
  'MyMedicalKit',
  'AggressiveChicken9000',
  'MyArmorMod',
  'BulletproofPajamas',
  'MyTraderConfig',
  'CursedCowboy',
  'MyLootRework',
  'HazmatHotdogStand',
  'MyClothingPack',
  'KarenSimulator',
  'MyHUDOverhaul',
  'BabyShark_Hostiles',
  'MyServerTools',
  'LegallyDistinctRifle',
  'MyVehiclePack',
  'ParkourGoatPack',
  'MyMapAddons',
  'ZombieKaraoke',
  'MyWeaponSkin',
  'ExistentialDreadHUD',
  'MyBaseBuildingExt',
  'TacticalRubberDuck',
];

function ModNameCycle() {
  const [idx, setIdx] = useState(0);
  const [text, setText] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = MOD_NAMES[idx % MOD_NAMES.length];
    let timer: ReturnType<typeof setTimeout>;
    if (!deleting && text === current) {
      timer = setTimeout(() => setDeleting(true), 1800);
    } else if (deleting && text === '') {
      setDeleting(false);
      setIdx((i) => i + 1);
    } else if (deleting) {
      timer = setTimeout(() => setText(text.slice(0, -1)), 32);
    } else {
      timer = setTimeout(() => setText(current.slice(0, text.length + 1)), 70);
    }
    return () => clearTimeout(timer);
  }, [text, deleting, idx]);

  return (
    <>
      {text}
      <span className={styles.cursor}>|</span>
    </>
  );
}

const AGENTS = [
  {name: 'dayz-script-specialist', desc: 'Enforce Script (modded classes, RPCs, replication)'},
  {name: 'dayz-config-specialist', desc: 'config.cpp, CfgPatches, CfgVehicles, hidden selections'},
  {name: 'dayz-asset-specialist', desc: '.p3d / .paa / .rvmat — textures, materials, model assets'},
  {name: 'dayz-object-builder', desc: '.p3d LODs, named selections, geometry properties'},
  {name: 'dayz-map-specialist', desc: 'Terrain Builder, DayZ Editor, map objects, clutter'},
  {name: 'dayz-ui-specialist', desc: '.layout files, HUD, menus, widget scripting'},
  {name: 'dayz-server-admin', desc: 'types.xml, init.c, cfggameplay.json, deployment'},
  {name: 'dayz-workbench-specialist', desc: 'Enfusion Workbench plugins and editor extensions'},
  {name: 'dayz-mod-debugger', desc: 'RPT, script.log, BattlEye log forensics'},
  {name: 'dayz-mod-reviewer', desc: 'Audit a mod folder for convention compliance'},
  {name: 'docs-wiki-sync', desc: 'Keep wiki in sync with canonical docs and skills'},
  {name: 'agent-creator', desc: 'Validate or create new agent definitions'},
];

function HeroBanner({title, tagline}: {title: string; tagline: string}) {
  const logoUrl = useBaseUrl('/img/AgenticZ_Logo.png');
  return (
    <header className={styles.heroBanner}>
      <div className={`container ${styles.heroInner}`}>
        <img src={logoUrl} alt="" className={styles.heroLogo} />
        <div className={styles.heroSubtitle}>
          <span className={styles.heroDivider} />
          AI Agent Stack for DayZ Modding
          <span className={styles.heroDivider} />
        </div>
        <h1 className={styles.heroTitle}>
          AGENTIC<span className={styles.heroTitleAccent}>-Z</span>
        </h1>
        <p className={styles.heroTagline}>Built Source Available to all</p>
        <div className={styles.heroButtons}>
          <Link className={styles.btnPrimary} to="/docs/intro">
            Get Started →
          </Link>
          <Link
            className={styles.btnSecondary}
            href="https://github.com/your-repo/agentic-z">
            View on GitHub
          </Link>
        </div>
        <div className={styles.heroMeta}>
          <span className={styles.heroMetaPre}>A</span>
          <span className={styles.heroMetaStudio}>DayZ Community</span>
          <span className={styles.heroMetaPost}>Development</span>
        </div>
      </div>
    </header>
  );
}

function StatsBand() {
  return (
    <section className={styles.statsBand}>
      <div className="container">
        <div className={styles.statsRow}>
          {STATS.map((s) => (
            <div className={styles.statBlock} key={s.label}>
              <div className={styles.statNum}>{s.num}</div>
              <div className={styles.statLabel}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ArchitectureSection() {
  return (
    <section className={`${styles.section} ${styles.sectionDark}`}>
      <div className="container">
        <h2 className={styles.sectionTitle}>Three-Layer Stack</h2>
        <div className={styles.sectionSubtitle}>// rules cascade from L1 → L3</div>
        <div className={styles.archGrid}>
          {LAYERS.map((l) => (
            <div className={styles.archCard} key={l.layer}>
              <div className={styles.archLayer}>{l.layer}</div>
              <div className={styles.archTitle}>{l.title}</div>
              <p className={styles.archDesc}>{l.desc}</p>
              <code className={styles.archPath}>{l.path}</code>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function AgentsSection() {
  return (
    <section className={`${styles.section} ${styles.sectionDarker}`}>
      <div className="container">
        <h2 className={styles.sectionTitle}>Specialist Agents</h2>
        <div className={styles.sectionSubtitle}>
          // domain experts at your terminal
        </div>
        <div className={styles.agentsGrid}>
          {AGENTS.map((a) => (
            <Link
              className={styles.agentCard}
              to={`/docs/agents/${a.name}`}
              key={a.name}>
              <div className={styles.agentName}>{a.name}</div>
              <div className={styles.agentDesc}>{a.desc}</div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function QuickStartSection() {
  return (
    <section className={`${styles.section} ${styles.sectionDark}`}>
      <div className="container">
        <h2 className={styles.sectionTitle}>Quick Start</h2>
        <div className={styles.sectionSubtitle}>// from clone to scaffolded mod</div>
        <div className={styles.terminalWrap}>
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
        <div style={{textAlign: 'center', marginTop: '2.5rem'}}>
          <Link className={styles.btnPrimary} to="/docs/dayz-modding">
            Full Workflow Guide →
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Agentic-Z — An AI Agent Stack for DayZ Modding">
      <HeroBanner title={siteConfig.title} tagline={siteConfig.tagline ?? ''} />
      <main>
        <StatsBand />
        <ArchitectureSection />
        <AgentsSection />
        <QuickStartSection />
      </main>
    </Layout>
  );
}
