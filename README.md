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

`kira` is the whole set. If you only want part of it, install the pieces instead — they are separate plugins in the same marketplace:

| Plugin | Contents | Install when |
| --- | --- | --- |
| `kira` | everything below | you want the lot in one command |
| `kira-engineering` | the 24 workflow skills | you don't work with Copilot review |
| `kira-copilot-review` | the `copilot-review` skill | you engage Copilot review, on any harness |
| `kira-copilot-review-hooks` | the four `PreToolUse` hooks | you're on Claude Code and want the hooks enforcing it |

The hooks are split out because they are Claude Code's own hook format, and another harness may read them and fail to run them ([an example](https://github.com/github/copilot-cli/issues/4001)). Installing `kira-copilot-review-hooks` pulls `kira-copilot-review` with it — the hooks encode that skill's rules and point at it by name. Install `kira` *or* the pieces, not both: the same skills would register twice, and the hooks would fire twice.

Skills are invoked under the name of the plugin that provides them — `/kira:code-review` from the bundle, `/kira-engineering:code-review` from the piece.

No plugin declares a `version`, so updates follow the repository's commits — `claude plugin update` picks up whatever has landed on the default branch.

## What's inside

**Writing and reviewing**

| Skill | What it does |
| --- | --- |
| `writing-for-agents` | How to write and revise a document an agent consumes — a skill, a `CLAUDE.md`, an ADR, a memory, a comment |
| `code-review` | Three-axis review of a diff — Standards, Spec, Docs — each in its own fresh-context sub-agent |
| `copilot-review` | Engaging automated PR review: what to act on, what to skip, when to stop — the one skill outside `kira-engineering` |

**Getting work done**

| Skill | What it does |
| --- | --- |
| `implement` / `implement-with-design` | Implement from a spec or tickets; the second also checks against a design prototype |
| `tdd` | Red-green-refactor, one seam at a time |
| `prototype` | A throwaway build to answer a design question |
| `get-pr-merged` | Take a draft PR through review to merge |
| `branch-worktree-cleanup` | Delete worktrees and branches whose PRs are done, with a confirmation table first |

**Thinking and planning**

| Skill | What it does |
| --- | --- |
| `wayfinder` | Map a body of work before committing to it |
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
| `qt-reference` | Answer Qt questions from the local `.qch` docs and source tree, not the web |
| `instruments-profiling` | Read macOS Instruments traces — CPU hotspots, hangs, lock contention |

## Hooks

Four `PreToolUse` hooks in `kira-copilot-review-hooks`, all advisory except the first, all concerned with GitHub PR review:

- `block-copilot-mention` — blocks `@copilot` in free text, which posts under your identity and starts a coding session on your account instead of requesting a review
- `hint-copilot-review-check` — `gh pr view --json reviewRequests` hides bot reviewers, so `[]` doesn't mean Copilot is absent
- `hint-pr-ready-monitor` — flipping a draft to ready requests a review; don't merge before it lands
- `hint-stale-gh` — warns when a `gh` result is likely stale

## Layout

```
.claude-plugin/         the `kira` bundle's own manifest, and the marketplace
hooks/                  the bundle's hook config, pointing into the plugin below
plugins/
  kira-engineering/
  kira-copilot-review/
  kira-copilot-review-hooks/
```

Each skill and hook script has exactly one home, under `plugins/`. The `kira` bundle owns no components of its own — its manifest points `skills` at the other plugins' directories, so installing it gets the same files, not copies of them.

## Setup

Several skills — `wayfinder`, `triage`, `to-tickets`, `to-spec`, `code-review` — read per-repo configuration that isn't part of this plugin: `docs/agents/issue-tracker.md`, `CONTEXT.md`, and `docs/adr/`. Run `setup-matt-pocock-skills` from [upstream](https://github.com/mattpocock/skills) once per repo to scaffold it.

## License

MIT — see [LICENSE](LICENSE), and [NOTICE](NOTICE) for the upstream attribution.
