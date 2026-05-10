<script setup lang="ts">
const base = import.meta.env.BASE_URL
const asset = (path: string) => `${base}${path}`

const heroLogoUrl = asset('brand/png/clawqueue-mascot-only.png')
const headerLogoUrl = asset('brand/png/clawqueue-logo-full-horizontal.png')
</script>

<template>
  <div class="cq-page">
    <header class="cq-topbar">
      <a class="cq-brand" href="/ClawQueue/">
        <img :src="headerLogoUrl" alt="ClawQueue" class="cq-header-wordmark" />
      </a>
      <div class="cq-topbar-actions">
        <a class="cq-link" href="/ClawQueue/guide/operator-workflow">Docs</a>
        <a class="cq-link" href="https://github.com/ClawQueue/ClawQueue">GitHub</a>
        <a class="cq-btn primary" href="/ClawQueue/start/getting-started">Get Started</a>
      </div>
    </header>

    <main class="cq-main">
      <section class="cq-hero">
        <div class="cq-hero-copy">
          <div class="cq-kicker">GitHub issues in. Agent work out.</div>
          <h1>Turn GitHub Issues into a local agent queue</h1>
          <p>
            ClawQueue keeps GitHub Issues and Projects as the durable work contract,
            then uses a local scheduler to pick eligible work, launch the right agent mode,
            and report results back to the issue.
          </p>
          <div class="cq-actions">
            <a class="cq-btn primary" href="/ClawQueue/start/getting-started">Get Started</a>
            <a class="cq-btn secondary" href="https://github.com/ClawQueue/ClawQueue">View GitHub</a>
          </div>
          <div class="cq-tags">
            <span>Local-first</span>
            <span>GitHub-native</span>
            <span>Markdown-configurable</span>
            <span>PR-reviewable</span>
          </div>
        </div>

        <div class="cq-hero-art">
          <div class="cq-art-card">
            <img :src="heroLogoUrl" alt="ClawQueue mascot" class="cq-mascot" />
          </div>
        </div>
      </section>

      <section class="cq-proof">
        <div class="cq-proof-card">
          <strong>GitHub holds the contract</strong>
          <span>Issues, labels, projects, comments, branches, PRs.</span>
        </div>
        <div class="cq-proof-card">
          <strong>Your machine runs the workers</strong>
          <span>OpenClaw, Claude Code, Codex, or other local runners.</span>
        </div>
        <div class="cq-proof-card">
          <strong>Humans still review the work</strong>
          <span>Results come back as comments, artifacts, and PR-ready changes.</span>
        </div>
      </section>

      <section class="cq-section cq-dark">
        <div class="cq-section-copy">
          <div class="cq-kicker dark">HOW IT WORKS</div>
          <h2>Issue-driven agent work, without losing the thread</h2>
          <div class="cq-flow-visual" aria-label="How ClawQueue works">
            <div><small>01</small><span>Issue</span></div>
            <div><small>02</small><span>Scheduler</span></div>
            <div><small>03</small><span>Agent Mode</span></div>
            <div><small>04</small><span>Local Runner</span></div>
            <div><small>05</small><span>Comment / PR</span></div>
          </div>
        </div>
        <pre class="cq-terminal"><code>$ python3 scripts/scheduler.py
[pick] eligible issue in Todo
[route] labels -> mode + agent
[run] local backend started
[report] comment + artifact + PR link</code></pre>
      </section>

      <section class="cq-grid-two">
        <article class="cq-card">
          <div class="cq-kicker">OWN PROJECTS</div>
          <h3>Operate your own queue</h3>
          <p>Run CQ against your own repos, boards, profiles, and worklog. Keep product, engineering, ops, and review in one GitHub-native loop.</p>
        </article>
        <article class="cq-card">
          <div class="cq-kicker">EXTERNAL REPOS</div>
          <h3>Contribute through a fork</h3>
          <p>Use the same issue-driven flow for outside projects: shape work into issues on your fork, dispatch locally, then open a cleaner upstream PR.</p>
        </article>
      </section>

      <section class="cq-final">
        <h2>Put your GitHub issues to work. Locally.</h2>
        <div class="cq-actions center">
          <a class="cq-btn primary" href="/ClawQueue/start/getting-started">Get Started</a>
          <a class="cq-btn secondary" href="/ClawQueue/guide/operator-workflow">Read Docs</a>
          <a class="cq-btn secondary" href="https://github.com/ClawQueue/ClawQueue">View GitHub</a>
        </div>
      </section>
    </main>
  </div>
</template>
