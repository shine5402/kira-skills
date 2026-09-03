---
name: branch-worktree-cleanup
description: Clean up stale worktrees and local branches whose PRs are merged or closed, with a confirmation table before anything is deleted. Use when the user asks to clean up branches or worktrees, or when disk space runs short.
---

# Branch & Worktree Cleanup

Find local branches and worktrees that are no longer active because their PRs are merged or closed, show a confirmation table, then delete them.

## Step-by-step procedure

### 1. Gather state

Run both in parallel:

```bash
git worktree list
git branch --format='%(refname:short)'
```

Drop this repo's long-lived branches from the candidate list — the default branch plus any other trunk it keeps (a release line, a staging branch). `gh repo view --json defaultBranchRef` names the first one; ask the user about the rest if the repo's convention isn't obvious.

### 2. Check PR status for every branch

```bash
gh pr list --state all --limit 300 --json headRefName,number,state,title
```

Match each local branch to a PR. Classify each as:

- **open** — skip, it's active work
- **merged** — candidate for deletion
- **closed (without merge)** — candidate for deletion by default; closures are almost always intentional (superseded by another PR, abandoned approach). If the closure reason looks ambiguous, note it in the confirmation table so the user can decide.
- **no_pr** — do NOT delete based on PR state alone; check for unique commits (step 3)

### 3. Check orphaned branches (no PR, no worktree)

For branches with no PR and no associated worktree, check if they carry unique work. Run per-branch (works in bash, Git Bash, and pwsh alike):

```bash
git log --oneline origin/develop..<branch>
```

- **0 unique commits** → safe to include in the deletion list (harness leftovers pointing at already-merged commits)
- **≥1 unique commit** → surface to the user with the commit list; do not delete without explicit confirmation

### 4. Show confirmation table

Present three sections before touching anything:

**Worktrees to remove + branches to delete**

| Worktree | Branch | PR / reason |
|---|---|---|
| `name` | `branch` | #NNN merged |

**Branches only to delete (no worktree)**

| Branch | PR / reason |
|---|---|
| `branch` | #NNN merged |

**KEPT (open PRs or ambiguous)**

List everything being skipped with the reason.

Then wait for the user to reply "go" (or any explicit confirmation).

### 5. Execute

**Always use `-f` / `--force` for both operations** — this repo uses submodules (worktree remove needs force) and squash-merges (branch delete needs force):

```bash
# Remove each worktree
git worktree remove -f .claude/worktrees/<name>

# Delete branches (after their worktrees are gone)
git branch -D <branch1> <branch2> ...
```

**Harness vs manually created worktrees:** worktrees under `.claude/worktrees/` were created by the Claude Code harness and are safe to remove once their branch is done. Worktrees at any other path (e.g. a sibling directory the user created manually with `git worktree add`) are not harness artifacts — ask the user explicitly whether to keep them before including them in the deletion list, even if their branch has a closed PR.

Worktrees with the `locked` flag require double-force (`git worktree remove --force --force`). Skip locked worktrees unless the user explicitly says to remove them.

### 6. Verify

```bash
git worktree list
git branch --format='%(refname:short)' | grep -vE '^(develop|release-candidate|release)$'
```

Confirm only the expected active worktrees and open-PR branches remain.

## What to skip (never delete without explicit user instruction)

- Any branch/worktree with an **open** PR
- Any **locked** worktree
- The trunk branches: `develop`, `release-candidate`, `release`
- Branches with ≥1 unique commit not reachable from `origin/develop` (surface these instead)

## Shell / platform notes

Stick to individual `git`/`gh` commands rather than bash `for` loops so the procedure works in bash, Git Bash on Windows, and pwsh alike.

**Windows quirks to watch for:**

- Git Bash and pwsh are separate environments; a shell opened inside Git Bash will not inherit pwsh `$PATH` entries and vice versa. Run git/gh commands directly in whichever shell the user has open.
- `git worktree remove` path separators: pass the path as-is from `git worktree list` output; don't convert slashes manually.
- On CMD/pwsh, quote branch names that contain `/` or `+` when passing to `git branch -D` (wrap in double quotes).

## Disk space note (macOS only)

Space freed by removing worktrees may not show up: Time Machine local snapshots can retain the deleted files. If the user expected space back and didn't get it, check `tmutil listlocalsnapshots /` and offer `tmutil deletelocalsnapshots <snapshot>` — **require confirmation** before deleting snapshots. `tmutil` doesn't exist on Windows; skip this on non-macOS hosts.
