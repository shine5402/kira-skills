---
name: qt-reference
description: Consult the local Qt install for Qt questions — .qch API docs first, the framework Src tree when docs don't settle it. Use when looking up any Qt API (signature, enum, property — prefer this over web search or context7), when investigating a Qt bug or unexpected Qt behavior, or when optimizing code that interfaces closely with Qt.
---

# Qt reference: local docs, then source

Docs first — `qtdoc.py` reads the `.qch` files bundled with the Qt install: version-exact, instant, no network. Open the Qt source only when the docs don't settle it: a Qt bug or unexpected behavior, an under-documented API, or optimizing Qt-interfacing code.

## API docs — qtdoc.py

```bash
python3 <this skill's directory>/qtdoc.py --qch-dir <docs dir> <command> ...
```

Python 3 stdlib only. Pass `--qch-dir` (or `QT_QCH_DIR`) from your remembered Qt docs location on every call — that works even in a fresh worktree whose `build/` is empty. On a first run with no remembered location, omit it: the tool derives the dir from `build/.bootstrap_qt_prefix` and prints the result as an `info:` line — save it to memory so later worktrees don't need the cache. When the `--qch-dir` you pass diverges from a present cache, the tool prints a `warning:` (but honors your path): the project retargeted Qt or the install moved — update your memory, docs dir and Src tree both. It errors only when there is neither a remembered path nor a cache.

Commands (`--qch-dir` goes before the subcommand):

- `search <query> [-n 50]` — find the right symbol when unsure of the exact name.
- `read <Class>` / `read <Class>::<member>` — class pages can be very large; whenever you know the member, use the `::member` form to get just that section.
- `page <filename.html>` — a doc page by filename (overviews, guides).
- `list` — available modules.
- `--raw` (on `read`/`page`) — raw HTML, for when the plain-text rendering loses formatting or code examples.

## Framework source — `<qt_root>/<version>/Src`

The source sits under the same Qt root as the docs (e.g. `~/Qt/6.10.1/Src`); match the version to the bootstrap prefix so the implementation you read is the one that actually runs. Standard Qt module layout — grep the relevant module rather than guessing a path:

```bash
rg -n "QWidget::setVisible" ~/Qt/6.10.1/Src/qtbase/src/widgets
```

`Src` is an optional installer component and may be absent. Then: ask the user to install it via the Maintenance Tool, read the online source (code.qt.io or the github.com/qt mirror, on the matching `v<version>` tag), or settle the question another way — but if the user explicitly asked you to read the Qt source, say you can't find a local copy instead of silently substituting.
