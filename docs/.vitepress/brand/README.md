# ClawQueue Design System

This is the root note for the current ClawQueue brand/design assets used by the docs site.

## What the docs site actually uses

The VitePress docs implementation currently uses:

- Header/root README logo: `docs/public/brand/png/clawqueue-logo-full-horizontal.png`
- Docs home hero mascot: `docs/public/brand/png/clawqueue-mascot-only.png`
- Favicons/app icons: `docs/public/brand/favicons/*`
- Public brand tokens: `docs/public/brand/brand-tokens.json`
- Public portable CSS tokens: `docs/public/brand/brand.css`
- VitePress implementation CSS: `docs/.vitepress/theme/style.css`
- VitePress custom home page: `docs/.vitepress/theme/components/HomePage.vue`

Use the PNG assets for the docs and README unless there is a strong reason to use SVG. The SVG files are wrappers around the approved high-resolution PNG artwork and mainly exist for compatibility.

## Visual direction in production docs

The docs site landed on:

- **Logo:** full horizontal ClawQueue logo in the top bar and root README.
- **Hero art:** mascot-only robot/claw illustration inside a soft radial card.
- **Primary surface:** clean white background with soft blue-gray cards.
- **Contrast section:** deep navy gradient panel for the workflow explanation.
- **CTA:** orange/red claw gradient buttons.
- **Typography:** `Space Grotesk` for headings, `Inter` for body, system monospace for terminal/code snippets.
- **Layout:** wide, minimal landing page with custom VitePress chrome hidden on the homepage.

## Core colors used in docs

The custom VitePress theme uses these active CSS variables:

```css
--cq-bg: #fff;
--cq-fg: #03143A;
--cq-muted: #5E6A7D;
--cq-border: #dde7f0;
--cq-claw: #E84312;
--cq-claw-hot: #FF5A18;
--cq-cyan: #1EC6FF;
--cq-night-fg: #eaf2fb;
--cq-gradient-claw: linear-gradient(135deg, #FF5A18 0%, #E84312 100%);
--cq-gradient-night: linear-gradient(135deg, #03143A 0%, #081C4D 58%, #102a4c 100%);
```

`docs/public/brand/brand.css` and `brand-tokens.json` are the portable/exported equivalents. If the docs theme changes, update those files and this README together.

## Main assets

### PNG

- `docs/public/brand/png/clawqueue-logo-full-horizontal.png` — primary website/root README logo
- `docs/public/brand/png/clawqueue-logo-stacked-square.png`
- `docs/public/brand/png/clawqueue-icon-with-queue.png` — recommended icon/favicon source
- `docs/public/brand/png/clawqueue-mascot-only.png` — docs homepage hero art
- `docs/public/brand/png/clawqueue-wordmark.png`
- `docs/public/brand/png/clawqueue-queue-symbol.png`

### SVG

- `docs/public/brand/svg/clawqueue-logo-full-horizontal.svg`
- `docs/public/brand/svg/clawqueue-logo-stacked-square.svg`
- `docs/public/brand/svg/clawqueue-icon-with-queue.svg`
- `docs/public/brand/svg/clawqueue-mascot-only.svg`
- `docs/public/brand/svg/clawqueue-wordmark.svg`
- `docs/public/brand/svg/clawqueue-queue-symbol.svg`

### Favicons / app icons

- `docs/public/brand/favicons/favicon-16.png`
- `docs/public/brand/favicons/favicon-32.png`
- `docs/public/brand/favicons/favicon-48.png`
- `docs/public/brand/favicons/favicon-64.png`
- `docs/public/brand/favicons/apple-touch-icon.png`
- `docs/public/brand/favicons/clawqueue-icon-128.png`
- `docs/public/brand/favicons/clawqueue-icon-192.png`
- `docs/public/brand/favicons/clawqueue-icon-256.png`
- `docs/public/brand/favicons/clawqueue-icon-512.png`

## Implementation notes

- The homepage is intentionally custom: `HomePage.vue` plus `style.css` hide default VitePress navigation/chrome on the homepage.
- Keep the root README logo path as `docs/public/brand/png/clawqueue-logo-full-horizontal.png`; do not use the old missing `docs/banner.svg` path.
- Keep docs links base-aware through VitePress where possible (`import.meta.env.BASE_URL` in Vue components).
- When changing assets, run `npm run docs:build` before committing.

## Source renders

The original latest renders used for this pack are kept in `docs/public/brand/source-renders/`.
