# kira-skills

The set of Claude Code skills I carry across every repo I work in, packaged as plugins so I never have to assemble it by hand again.

Most of these started as [Matt Pocock's skills](https://github.com/mattpocock/skills), with my own changes applied — some heavily rewritten, some copied as-is. I use a fraction of what that repo offers, so this is a deliberate subset rather than a mirror: the ones that actually earn their place in my workflow. A few are mine, written for one project and kept because they turned out to travel.

It's public because some of it may be useful to colleagues and friends. It's shaped around how I work, so treat it as a starting point rather than a standard.

Everything here targets the Claude Code harness: the skill format, the plugin and marketplace manifests, and the hook event names are all its own. Another harness would need these adapted, not just copied.

## Install

```bash
claude plugin marketplace add shine5402/kira-skills
claude plugin install kira@kira-skills
```

`kira` is the workflow set. Copilot is opt-in, as separate plugins in the same marketplace:

| Plugin | Contents | Install when |
| --- | --- | --- |
| `kira` | the 29 workflow skills | always — this is the set |
| `kira-engineering` | the same skills as `kira` | you prefer the longer name; install one of the two, never both |
| `kira-copilot-review` | the `copilot-review` skill | Copilot is one of your PR reviewers, on any harness |
| `kira-copilot-review-hooks` | the three `PreToolUse` hooks | you're on Claude Code and want the hooks guarding those Copilot calls |

`kira` is an alias: its manifest points at `kira-engineering`'s skill directory, so the two install the same files and register the same skills twice if both are on. The hooks are split out because they are Claude Code's own hook format, and another harness may read them and fail to run them ([an example](https://github.com/github/copilot-cli/issues/4001)). Installing `kira-copilot-review-hooks` pulls `kira-copilot-review` with it — the hooks point at that skill by name.

Skills are invoked under the name of the plugin that provides them — `/kira:spec-review` from `kira`, `/kira-engineering:spec-review` from the longer name.

No plugin declares a `version`, so updates follow the repository's commits — `claude plugin update` picks up whatever has landed on the default branch.

## What's inside

**Writing and reviewing**

| Skill | What it does |
| --- | --- |
| `writing-for-agents` | How to write and revise a document an agent consumes — a skill, a `CLAUDE.md`, an ADR, a memory, a comment |
| `spec-review` | Three-axis review of a diff against what's written down — Standards, Spec, Docs — each in its own fresh-context sub-agent |
| `second-opinion-review` | The gate before a PR merges: one round from an independent agentic reviewer, requested deliberately, waived only by the user |
| `pr` | The shape a PR body should take — a summary as the smallest visual that makes the change clear, before/after evidence, and a merge-danger call |
| `copilot-review` | GitHub Copilot as that reviewer: requesting a round, checking it's attached, telling when it landed — in `kira-copilot-review` |

**Getting work done**

| Skill | What it does |
| --- | --- |
| `implement` / `implement-with-design` | Implement from a spec or tickets; the second also checks against a design prototype |
| `implement-spec` | Build a whole spec on one integration branch — work the tickets as a task graph, running implementers across the ready frontier, then review |
| `implement-in-worktree` | `implement`, isolated in a dedicated worktree and closed out with a PR |
| `tdd` | Red-green-refactor, one seam at a time |
| `prototype` | A throwaway build to answer a design question |
| `get-pr-merged` | Take a draft PR through review to merge |
| `branch-worktree-cleanup` | Delete worktrees and branches whose PRs are done, with a confirmation table first |

**Thinking and planning**

| Skill | What it does |
| --- | --- |
| `wayfinder` | Map a body of work too big for one session, and land it stage by stage |
| `triage` | Sort incoming issues into actionable state |
| `to-spec` / `to-tickets` | Turn a discussion into a spec, or a spec into tickets |
| `domain-modeling` / `codebase-design` | Sharpen a domain model; design deep modules |
| `grilling` / `grill-me` / `grill-with-docs` | Stress-test a plan or decision against real pushback |
| `research` | Investigate a question against primary sources and write it up |

**Session and platform**

| Skill | What it does |
| --- | --- |
| `wait-what` | That last message didn't land — re-pitch it with context, in plain language and the repo's own terms |
| `handoff` | Hand the current state to the next session |
| `prepare-compact` / `trim-memory` | Keep context and memory from silting up |
| `retro` | Suggest fixes to the agent's environment after a session — navigation, automated checks, coding standards, steering files, tooling |
| `qt-reference` | Answer Qt questions from the local `.qch` docs and source tree, not the web |
| `instruments-profiling` | Read macOS Instruments traces — CPU hotspots, hangs, lock contention |

## Hooks

Three `PreToolUse` hooks in `kira-copilot-review-hooks`, all advisory except the first, all concerned with Copilot as a PR reviewer:

- `block-copilot-mention` — blocks `@copilot` in free text, which posts under your identity and starts a coding session on your account instead of requesting a review
- `hint-copilot-review-check` — `gh pr view --json reviewRequests` hides bot reviewers, so `[]` doesn't mean Copilot is absent
- `hint-stale-gh` — warns when the installed `gh` is too old for `--add-reviewer @copilot`, which then exits 0 having requested nothing

## Layout

```
.claude-plugin/         the `kira` alias's own manifest, and the marketplace
plugins/
  kira-engineering/
  kira-copilot-review/
  kira-copilot-review-hooks/
```

Each skill and hook script has exactly one home, under `plugins/`. The `kira` alias owns no components of its own — its manifest points `skills` at `kira-engineering`'s directory, so installing it gets the same files, not copies of them.

## Cross-references

Skills name each other plainly, by the `name` in the target's frontmatter — `Use the Skill tool with "tdd"` — never with a plugin prefix. The prefix is `kira:` or `kira-engineering:` depending on which plugin a repo installed, and a harness without plugin namespacing (opencode, where these are symlinked) has none at all, so a prefixed call either misses or sends the agent hunting for the plugin that owns it.

Keep names clear of Claude Code's bundled skills (`code-review`, `simplify`, `security-review`, …): a shared name turns a plain cross-reference into a guess between two skills.

## Setup

Several skills — `wayfinder`, `triage`, `to-tickets`, `to-spec`, `implement-spec`, `spec-review`, and `pr` — read per-repo configuration that isn't part of this plugin: `docs/agents/issue-tracker.md`, `CONTEXT.md`, and `docs/adr/`. Run `setup-matt-pocock-skills` from [upstream](https://github.com/mattpocock/skills) once per repo to scaffold it. Note that upstream v1.3 renamed the domain doc to `GLOSSARY.md`; this set still reads `CONTEXT.md`, so if the scaffolder writes `GLOSSARY.md`, rename it back — `git mv GLOSSARY.md CONTEXT.md` (and likewise `GLOSSARY-MAP.md` → `CONTEXT-MAP.md`).

## License

MIT — see [LICENSE](LICENSE), and [NOTICE](NOTICE) for the upstream attribution.
