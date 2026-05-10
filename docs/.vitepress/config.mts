import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ClawQueue',
  description: 'Local GitHub issue dispatch for operator-controlled AI agents.',
  lang: 'en-US',
  cleanUrls: true,
  lastUpdated: true,
  base: '/ClawQueue/',
  outDir: './site',
  head: [
    ['link', { rel: 'icon', type: 'image/png', sizes: '64x64', href: '/ClawQueue/brand/favicons/favicon-64.png' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '48x48', href: '/ClawQueue/brand/favicons/favicon-48.png' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/ClawQueue/brand/favicons/favicon-32.png' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/ClawQueue/brand/favicons/favicon-16.png' }],
    ['link', { rel: 'shortcut icon', href: '/ClawQueue/favicon.ico' }],
    ['link', { rel: 'apple-touch-icon', sizes: '180x180', href: '/ClawQueue/brand/favicons/apple-touch-icon.png' }],
    ['link', { rel: 'manifest', href: '/ClawQueue/brand/site.webmanifest' }],
    ['meta', { name: 'theme-color', content: '#03143A' }]
  ],
  themeConfig: {
    logo: '/brand/svg/clawqueue-icon-with-queue.svg',
    siteTitle: 'ClawQueue',
    nav: [
      { text: 'Guide', link: '/start/getting-started' },
      { text: 'Config', link: '/guide/configuration' },
      { text: 'Roadmap', link: '/roadmap' },
      { text: 'GitHub', link: 'https://github.com/ClawQueue/ClawQueue' }
    ],
    sidebar: [
      {
        text: 'Start',
        items: [
          { text: 'What is ClawQueue?', link: '/' },
          { text: 'Getting started', link: '/start/getting-started' }
        ]
      },
      {
        text: 'Guide',
        items: [
          { text: 'Operator workflow', link: '/guide/operator-workflow' },
          { text: 'Configuration', link: '/guide/configuration' },
          { text: 'Profiles', link: '/guide/profiles' },
          { text: 'Artifacts', link: '/guide/artifacts' }
        ]
      },
      {
        text: 'Reference',
        items: [
          { text: 'Commands', link: '/reference/commands' },
          { text: 'Safety model', link: '/reference/safety' },
          { text: 'Roadmap', link: '/roadmap' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/ClawQueue/ClawQueue' }
    ],
    search: {
      provider: 'local'
    },
    editLink: {
      pattern: 'https://github.com/ClawQueue/ClawQueue/edit/main/docs/:path',
      text: 'Edit this page on GitHub'
    },
    footer: {
      message: 'GitHub issues in. Agent work out.',
      copyright: 'MIT Licensed'
    }
  },
  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark'
    }
  }
})
