import type {ReactNode} from 'react';
import {useEffect, useState} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

import styles from './index.module.css';

const STATS = [
  {num: '12', label: 'Specialist Agents'},
  {num: '20', label: 'Slash Skills'},
  {num: '3', label: 'Agent CLIs'},
  {num: '2', label: 'MCP Servers'},
];

const LAYERS = [
  {
    layer: 'L1',
    title: 'Rules',
    essence: 'One ruleset, multiple platforms.',
    body: 'Whether you use Claude Code, Codex, or Gemini, your AI cuts the apologies, reaches for the right tool, and never mixes your personal preferences with the project’s rules.',
    path: 'CLAUDE.md / AGENTS.md / GEMINI.md',
  },
  {
    layer: 'L2',
    title: 'Conventions',
    essence: 'One DayZ playbook, every agent.',
    body: 'From day one, your AI knows how to inherit cleanly from vanilla classes, which suffix every texture needs, and why some modded classes silently fail. The DayZ quirks that can take weeks to learn.',
    path: '.claude/skills/_shared/dayz-conventions.md',
  },
  {
    layer: 'L3',
    title: 'Agents & Skills',
    essence: 'Specialists for thinking, commands for doing.',
    body: 'Ask the script specialist about a tricky modded class. Hand the mod-debugger your crash log. Run /dayz-build-pbo to pack and deploy. The work is one step away, every time.',
    path: 'Claude Code → dayz-script-specialist',
  },
];

const RAG_FEATURES = [
  {
    title: 'Source Code Search',
    essence: 'Vanilla DayZ, vector-indexed.',
    body: 'Your AI can search the entire engine source: Enforce Script, configs, layouts, materials. Ask “how does the survival HUD bind player health?” and it pulls the actual vanilla code instead of guessing.',
    tool: 'search_dayz_source',
  },
  {
    title: 'Community Wiki Search',
    essence: 'Bohemia’s wiki, semantically searchable.',
    body: 'The community-maintained engine docs and scripting guides, indexed alongside the source. Ask about an Enfusion event lifecycle or a config inheritance pattern, and it pulls the wiki page that actually explains it.',
    tool: 'search_dayz_wiki',
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
            Get Started <span className={styles.btnArrow}>→</span>
          </Link>
          <Link
            className={styles.btnSecondary}
            href="https://github.com/DayZ-n-Chill/Agentic-Z">
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
        <p className={styles.sectionLead}>
          Add Agentic-Z to your project and your AI gets three layers of context: how it should behave, what it knows about DayZ, and the slash commands you’d otherwise wire up by hand. It walks in already speaking DayZ instead of starting at zero.
        </p>
        <div className={styles.archGrid}>
          {LAYERS.map((l) => (
            <div className={styles.archCard} key={l.layer}>
              <div className={styles.archLayer}>{l.layer}</div>
              <div className={styles.archTitle}>{l.title}</div>
              <p className={styles.archEssence}>{l.essence}</p>
              <p className={styles.archDesc}>{l.body}</p>
              <code className={styles.archPath}>{l.path}</code>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RagSection() {
  return (
    <section className={`${styles.section} ${styles.sectionDark}`}>
      <div className="container">
        <h2 className={styles.sectionTitle}>On-Tap Reference</h2>
        <div className={styles.sectionSubtitle}>// vanilla source + wiki, indexed locally</div>
        <p className={styles.sectionLead}>
          Your AI doesn’t just know DayZ in general. It can read the actual engine source and the community wiki on demand, indexed locally on your machine, without you copy-pasting code into the chat.
        </p>
        <div className={`${styles.archGrid} ${styles.archGrid2col}`}>
          {RAG_FEATURES.map((f) => (
            <div className={styles.archCard} key={f.title}>
              <div className={styles.archLayer}>RAG</div>
              <div className={styles.archTitle}>{f.title}</div>
              <p className={styles.archEssence}>{f.essence}</p>
              <p className={styles.archDesc}>{f.body}</p>
              <code className={styles.archPath}>{f.tool}</code>
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
          // DayZ specialists at your terminal
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

function StyleGuideSection() {
  return (
    <section className={`${styles.section} ${styles.sectionDarker}`}>
      <div className="container">
        <h2 className={styles.sectionTitle}>The Style Guide</h2>
        <div className={styles.sectionSubtitle}>// the way DayZ pros write Enforce Script</div>
        <p className={styles.sectionLead}>
          Every agent that writes Enforce Script reads the same style guide: naming, indentation, modded-class patterns, the works. Mirrored locally so the rules apply offline and travel with every clone of Agentic-Z.
        </p>
        <p className={styles.styleGuideCredit}>
          Sourced from <a href="https://github.com/TrueDolphin/references/wiki/EnScript-(Enforce-Script)-Style-Guide" target="_blank" rel="noopener noreferrer">TrueDolphin/references</a>, used with thanks.
        </p>
      </div>
    </section>
  );
}

function ContributorSection() {
  return (
    <section className={`${styles.section} ${styles.sectionDarker}`}>
      <div className="container">
        <h2 className={styles.sectionTitle}>Become a Contributor</h2>
        <div className={styles.sectionSubtitle}>// built by modders, for modders</div>
        <p className={styles.sectionLead}>
          Every agent, skill, and convention in Agentic-Z started as a real problem someone hit while shipping a mod. Pitch a skill, fix a bug, propose an agent, or share what you built. Whether you’re a seasoned Enforce Script dev, a server admin, a 3D artist, or learning DayZ modding for the first time, your contributions matter.
        </p>
        <div className={styles.heroButtons} style={{marginTop: '2rem'}}>
          <Link
            className={styles.btnPrimary}
            href="https://discord.gg/dayznchill">
            Join the Discord →
          </Link>
          <Link
            className={styles.btnSecondary}
            href="https://github.com/DayZ-n-Chill/Agentic-Z">
            View on GitHub
          </Link>
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
        <RagSection />
        <StyleGuideSection />
        <QuickStartSection />
        <ContributorSection />
      </main>
    </Layout>
  );
}
