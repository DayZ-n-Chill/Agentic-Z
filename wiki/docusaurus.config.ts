import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Agentic-Z',
  tagline: 'An AI Agent Stack for DayZ Modding',
  favicon: 'img/AgenticZ_Logo.png',

  future: {
    v4: true,
  },

  url: 'https://agentic-z.com',
  baseUrl: '/',

  organizationName: 'DayZ-n-Chill',
  projectName: 'Agentic-Z',

  onBrokenLinks: 'throw',

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  themes: ['@docusaurus/theme-mermaid'],

  plugins: [
    [
      '@docusaurus/plugin-ideal-image',
      {
        quality: 85,
        max: 1200,
        min: 480,
        steps: 3,
        disableInDev: true,
      },
    ],
    [
      'plugin-image-zoom',
      {
        selector: '.markdown img',
        background: {
          light: 'rgba(244, 241, 230, 0.9)',
          dark: 'rgba(15, 15, 10, 0.92)',
        },
      },
    ],
  ],

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          path: 'docs',
          routeBasePath: 'docs',
        },
        blog: {
          path: 'blog',
          routeBasePath: 'changelog',
          blogTitle: 'Changelog',
          blogDescription: 'Notable changes and releases for Agentic-Z.',
          blogSidebarTitle: 'All releases',
          showReadingTime: false,
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/AgenticZ_Logo.png',
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Agentic-Z',
      logo: {
        alt: 'Agentic-Z Logo',
        src: 'img/AgenticZ_Logo.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {to: '/changelog', label: 'Changelog', position: 'left'},
        {
          type: 'html',
          position: 'right',
          value: '<span class="navbar-os-badge">Source Available</span>',
        },
        {
          href: 'https://github.com/DayZ-n-Chill/Agentic-Z',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {
              label: 'Introduction',
              to: '/docs/intro',
            },
            {
              label: 'DayZ Modding Guide',
              to: '/docs/dayz-modding',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'Discord',
              href: 'https://discord.gg/dayz',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'Changelog',
              to: '/changelog',
            },
            {
              label: 'GitHub',
              href: 'https://github.com/DayZ-n-Chill/Agentic-Z',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Brian Orr (DayZ n' Chill). Source available. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['cpp', 'csharp', 'json', 'powershell', 'bash'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
