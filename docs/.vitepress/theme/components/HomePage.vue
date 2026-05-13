<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'

type HomepageCard = { title: string; details: string }

const base = import.meta.env.BASE_URL
const a = (p: string) => `${base}${p}`
const icon = a('brand/png/clawqueue-icon-with-queue.png')
const mascot = a('brand/png/clawqueue-icon-with-queue.png')

const { frontmatter } = useData()
const homepage = computed(() => frontmatter.value.homepage ?? {})
const signals = computed<string[]>(() => frontmatter.value.signals ?? [
  'Local-first',
  'GitHub-native',
  'Markdown-configurable',
  'PR-reviewable'
])
const lede = computed(() => homepage.value.lede ?? 'ClawQueue keeps GitHub Issues and Projects as the durable work contract, then uses a local scheduler to pick eligible work, launch the right agent mode, and report results back to the issue.')
const relationship = computed(() => homepage.value.relationship ?? '')
const proof = computed<HomepageCard[]>(() => homepage.value.proof ?? [
  { title: 'GitHub holds the contract', details: 'Issues, labels, projects, comments, branches, PRs.' },
  { title: 'Your machine runs the workers', details: 'OpenClaw, Claude Code, Codex, or other local runners.' },
  { title: 'Humans review the work', details: 'Output returns as comments, artifacts, and PR-ready changes.' }
])
const how = computed(() => homepage.value.how ?? {})
const howTitle = computed(() => how.value.title ?? 'Issue-driven agent work — without losing the thread')
const howDescription = computed(() => how.value.description ?? 'Every tick of the scheduler resolves a single eligible issue, runs a configured local backend, and writes the result back where humans can audit it.')
const howSteps = computed<HomepageCard[]>(() => how.value.steps ?? [
  { title: 'Issue', details: 'A task lands in GitHub Issues or Projects.' },
  { title: 'Scheduler', details: 'CQ checks status, locks, attempts and policy.' },
  { title: 'Agent Mode', details: 'Labels resolve to the right mode + role.' },
  { title: 'Local Runner', details: 'OpenClaw, Codex, Claude Code — your choice.' },
  { title: 'Comment / PR', details: 'Result returns to the issue, ready to review.' }
])
const twoDigit = (n: number) => String(n + 1).padStart(2, '0')
</script>

<template>
  <div class="cq-page">
    <header class="cq-topbar cq-wrap">
      <a class="cq-brand" href="/ClawQueue/">
        <img :src="icon" alt="ClawQueue" />
        <span>
          <span class="nm"><span class="x">Claw</span>Queue</span>
          <span class="tg">LOCAL · OPERATOR · v0</span>
        </span>
      </a>
      <nav class="cq-nav">
        <a href="/ClawQueue/start/getting-started">Get Started</a>
        <a href="/ClawQueue/guide/operator-workflow">Workflow</a>
        <a href="/ClawQueue/reference/commands">Reference</a>
        <a href="/ClawQueue/roadmap">Roadmap</a>
        <a class="cq-btn primary" href="https://github.com/ClawQueue/ClawQueue">View on GitHub →</a>
      </nav>
    </header>

    <section class="cq-hero cq-wrap">
      <div>
        <span class="cq-kicker"><span class="dot"></span>GitHub issues in · agent work out</span>
        <h1>Turn GitHub Issues into a <em>local agent queue</em>.</h1>
        <p class="lede">{{ lede }}</p>
        <p v-if="relationship" class="lede secondary">{{ relationship }}</p>
        <div class="cq-actions">
          <a class="cq-btn primary" href="/ClawQueue/start/getting-started">Get Started</a>
          <a class="cq-btn secondary" href="/ClawQueue/guide/operator-workflow">Read the Docs</a>
        </div>
        <div class="cq-pills">
          <span v-for="signal in signals" :key="signal" class="cq-pill"><span class="glyph">●</span>{{ signal }}</span>
        </div>
      </div>
      <div class="cq-hero-art">
        <div class="cq-hero-mascot">
          <img :src="mascot" alt="ClawQueue claw with queue dial" />
        </div>
        <div class="cq-float f1">
          <span class="lbl">Issue</span>
          <span class="v">#128 · refactor scheduler</span>
        </div>
        <div class="cq-float f2">
          <span class="lbl">Label</span>
          <span class="v">agent:fix</span>
          <span class="badge">routed</span>
        </div>
        <div class="cq-float f3">
          <span class="lbl">Mode</span>
          <span class="v">code-review</span>
        </div>
        <div class="cq-float f4">
          <span class="lbl">Status</span>
          <span class="v">PR opened ✓</span>
        </div>
      </div>
    </section>

    <section class="cq-wrap">
      <div class="cq-proof">
        <div v-for="(card, index) in proof" :key="card.title" class="cq-proof-card">
          <span class="num">{{ twoDigit(index) }}</span>
          <strong>{{ card.title }}</strong>
          <span>{{ card.details }}</span>
        </div>
      </div>
    </section>

    <section class="cq-section cq-wrap">
      <div class="cq-night">
        <div class="cq-section-head">
          <span class="cq-kicker cyan"><span class="dot"></span>How it works</span>
          <h2>{{ howTitle }}</h2>
          <p>{{ howDescription }}</p>
        </div>
        <div class="cq-flow">
          <div v-for="(step, index) in howSteps" :key="step.title" class="cq-flow-step"><span class="num">{{ twoDigit(index) }}</span><span class="t">{{ step.title }}</span><span class="d">{{ step.details }}</span></div>
        </div>
        <pre class="cq-terminal"><code><span class="prompt">$</span> <span class="cmd">python3 scripts/scheduler.py</span>
<span class="dim">[</span><span class="key">pick</span><span class="dim">]</span> eligible issue in <span class="ok">Todo</span>
<span class="dim">[</span><span class="key">route</span><span class="dim">]</span> labels → mode + agent
<span class="dim">[</span><span class="key">run</span><span class="dim">]</span> local backend started
<span class="dim">[</span><span class="key">report</span><span class="dim">]</span> comment + artifact + PR link <span class="ok">✓</span></code></pre>
      </div>
    </section>

    <section class="cq-section cq-wrap">
      <div class="cq-section-head">
        <span class="cq-kicker"><span class="dot"></span>Why local-first</span>
        <h2>Small surface. Inspectable policy. Reviewable output.</h2>
        <p>ClawQueue is intentionally a thin dispatch layer — not a hosted workflow suite — so you can read it, audit it, and modify it.</p>
      </div>
      <div class="cq-grid four">
        <div class="cq-card"><div class="ico">⌂</div><h3>Private by default</h3><p>Secrets and runtime context stay on your machine.</p></div>
        <div class="cq-card cyan"><div class="ico">⇄</div><h3>No vendor lock-in</h3><p>Swap runners without losing the task contract.</p></div>
        <div class="cq-card navy"><div class="ico">≡</div><h3>Inspectable policy</h3><p>Routing and behavior live in markdown/config you can patch fast.</p></div>
        <div class="cq-card"><div class="ico">✓</div><h3>Reviewable output</h3><p>Final state stays in GitHub where humans can judge it.</p></div>
      </div>
    </section>

    <section class="cq-section cq-wrap">
      <div class="cq-section-head">
        <span class="cq-kicker"><span class="dot"></span>Use it for</span>
        <h2>Your own projects, or contributions through a fork</h2>
      </div>
      <div class="cq-grid two">
        <div class="cq-card">
          <div class="ico">◴</div>
          <h3>Operate your own queue</h3>
          <p>Run CQ against your own repos, boards, profiles, and worklog. Keep product, engineering, ops, and review inside one GitHub-native loop.</p>
        </div>
        <div class="cq-card dark">
          <div class="ico">↗</div>
          <h3>Contribute through a fork</h3>
          <p>Use the same issue-driven flow for outside projects. Shape work into issues on your fork, dispatch locally, then open a cleaner upstream PR.</p>
        </div>
      </div>
    </section>

    <section class="cq-section cq-wrap">
      <div class="cq-spec">
        <div>
          <span class="cq-kicker"><span class="dot"></span>Minimal config</span>
          <h3>One yaml. One operator. One queue.</h3>
          <p>Keep dispatch policy, routing, and artifact destinations in a tiny, readable file. Patch it the way you'd patch any markdown.</p>
          <a class="cq-btn secondary" href="/ClawQueue/guide/configuration">See full config →</a>
        </div>
        <pre><code><span class="com"># clawqueue.yml</span>
<span class="key">projects</span>:
  - <span class="key">repo</span>: <span class="str">your-org/your-repo</span>
    <span class="key">dispatch_statuses</span>: [<span class="str">Todo</span>]
<span class="key">routing</span>:
  <span class="key">agent_roles</span>:
    <span class="key">cto</span>: <span class="str">cto</span>
    <span class="key">cmo</span>: <span class="str">cmo</span>
    <span class="key">reviewer</span>: <span class="str">reviewer</span>
<span class="key">artifacts</span>:
  <span class="key">backend</span>: <span class="str">local</span>
  <span class="key">path</span>: <span class="str">.clawqueue/boards</span>
  <span class="key">commit</span>: <span class="str">false</span></code></pre>
      </div>
    </section>

    <section class="cq-section cq-wrap">
      <div class="cq-section-head">
        <span class="cq-kicker"><span class="dot"></span>Honest scope</span>
        <h2>What ClawQueue is — and what it isn't</h2>
      </div>
      <div class="cq-compare">
        <div class="col is">
          <h3>ClawQueue is <span class="tag">yes</span></h3>
          <ul>
            <li>A local GitHub issue dispatcher</li>
            <li>A way to turn labels into agent modes</li>
            <li>A reviewable workflow for human-agent work</li>
            <li>A small layer you can read and modify</li>
          </ul>
        </div>
        <div class="col isnot">
          <h3>ClawQueue is not <span class="tag">no</span></h3>
          <ul>
            <li>A hosted PM suite</li>
            <li>A magical autonomous company in a box</li>
            <li>A secure multi-tenant executor</li>
            <li>A replacement for human review</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="cq-wrap">
      <div class="cq-cta">
        <h2>Put your GitHub issues to work. Locally.</h2>
        <p>Start with the docs, wire up one board, and let CQ pick one safe issue at a time.</p>
        <div class="cq-actions" style="justify-content:center">
          <a class="cq-btn primary" href="/ClawQueue/start/getting-started">Get Started</a>
          <a class="cq-btn ghost" href="/ClawQueue/guide/operator-workflow">Read the Workflow</a>
          <a class="cq-btn ghost" href="https://github.com/ClawQueue/ClawQueue">View GitHub</a>
        </div>
      </div>
    </section>

    <footer class="cq-footer cq-wrap">
      <div class="left">
        <img :src="icon" alt="" />
        <span>ClawQueue · GitHub issues in. Agent work out.</span>
      </div>
      <div class="right">
        <a href="/ClawQueue/start/getting-started">Get Started</a>
        <a href="/ClawQueue/guide/operator-workflow">Workflow</a>
        <a href="https://github.com/ClawQueue/ClawQueue">GitHub</a>
        <a href="/ClawQueue/roadmap">Roadmap</a>
      </div>
    </footer>
  </div>
</template>
