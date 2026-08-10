#!/usr/bin/env python3
"""
Qt Local Documentation Reader

Reads Qt .qch (Qt Compressed Help) files — which are SQLite databases —
to look up class/method/enum documentation from the local Qt installation.

Usage:
    qtdoc.py search <query>                  # Search symbols matching query
    qtdoc.py read <class_or_member>          # Read documentation for a class or member
    qtdoc.py read <class_or_member> --raw    # Output raw HTML instead of plain text
    qtdoc.py list                            # List all available .qch modules

The .qch files contain:
  - IndexTable: symbol name -> file ID + anchor
  - FileNameTable: file ID -> HTML filename + title
  - FileDataTable: file ID -> qCompress'd HTML blob (4-byte BE size + zlib)
"""

import argparse
import glob
import html.parser
import os
import re
import sqlite3
import struct
import sys
import zlib

# Documentation path — set via --qch-dir or QT_QCH_DIR env var, or auto-resolved
# from the ACE Studio bootstrap Qt-prefix cache (see resolve_qch_dir).
DEFAULT_QCH_DIR = os.environ.get("QT_QCH_DIR", "")

# Bootstrap records the chosen Qt prefix here (relative to the repo root), e.g.
#   /Users/<user>/Qt/6.10.1/macos   or   C:/Qt/6.10.1/msvc2022_64
BOOTSTRAP_QT_PREFIX_CACHE = os.path.join("build", ".bootstrap_qt_prefix")


def find_bootstrap_cache():
    """Locate build/.bootstrap_qt_prefix by walking up from CWD, then falling
    back to the repo root inferred from this script's location. Returns the file
    path or None."""
    candidates = []
    d = os.getcwd()
    while True:
        candidates.append(os.path.join(d, BOOTSTRAP_QT_PREFIX_CACHE))
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # This script lives beside its SKILL.md, so the
    # repo root is four os.path.dirname() levels up (qtdoc.py → qt-reference →
    # skills → .claude → repo). This also resolves correctly inside a git
    # worktree, which carries its own .claude/skills copy and its own build/.
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    candidates.append(os.path.join(repo_root, BOOTSTRAP_QT_PREFIX_CACHE))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def qch_dir_from_qt_prefix(prefix):
    """Derive the .qch docs directory from a Qt kit prefix.

    The Qt Maintenance Tool lays out, for a prefix like .../Qt/6.10.1/macos:
        version = 6.10.1                 (parent dir name)
        qt_root = .../Qt                 (two levels up)
        qch_dir = .../Qt/Docs/Qt-6.10.1  (sibling Docs/Qt-<version>)
    The same layout holds on Windows (only the kit name differs)."""
    prefix = prefix.rstrip("/\\")
    version = os.path.basename(os.path.dirname(prefix))
    qt_root = os.path.dirname(os.path.dirname(prefix))
    return os.path.join(qt_root, "Docs", f"Qt-{version}")


def read_cache_qch_dir():
    """Read build/.bootstrap_qt_prefix and derive its docs dir. Returns
    (qch_dir, prefix, cache_path); any element is None if unavailable."""
    cache = find_bootstrap_cache()
    if cache is None:
        return None, None, None
    with open(cache, encoding="utf-8") as f:
        prefix = f.read().strip()
    if not prefix:
        return None, None, cache
    return qch_dir_from_qt_prefix(prefix), prefix, cache


def resolve_qch_dir(explicit):
    """Resolve the .qch directory. Returns (qch_dir, error_message).

    You (the caller) are expected to pass your known Qt docs dir via --qch-dir /
    QT_QCH_DIR — that works even in a fresh worktree with no bootstrap cache. The
    bootstrap Qt-prefix cache is the ground truth when present: if the explicit
    path diverges from it, we WARN (on stderr) but honor the explicit path, so a
    stale remembered location surfaces itself. With no explicit path we fall back
    to auto-deriving from the cache."""
    cache_qch, prefix, cache = read_cache_qch_dir()

    if explicit:
        if cache_qch and os.path.normpath(explicit) != os.path.normpath(cache_qch):
            print(
                f"warning: --qch-dir {explicit} differs from the bootstrap-recorded "
                f"Qt docs dir {cache_qch} (Qt prefix {prefix!r} in {cache}). If this "
                "came from a remembered Qt location, it may be stale — the project's "
                "targeted Qt version or install path likely changed; update your "
                "memory (both the docs dir and the Src tree).",
                file=sys.stderr,
            )
        return explicit, None

    if cache is None:
        return None, (
            "Could not determine the Qt docs directory: no bootstrap Qt-prefix "
            f"cache ({BOOTSTRAP_QT_PREFIX_CACHE}) found, and no --qch-dir / "
            "QT_QCH_DIR given. Pass your known Qt docs dir, or run ./bootstrap.sh."
        )
    if cache_qch is None:
        return None, f"Bootstrap cache {cache} is empty; re-run ./bootstrap.sh."
    if not os.path.isdir(cache_qch):
        return None, (
            f"Derived Qt docs directory does not exist: {cache_qch} (from Qt prefix "
            f"{prefix!r} in {cache}). The Qt 'Docs' component may not be installed; "
            "install it via the Qt Maintenance Tool or pass --qch-dir."
        )
    print(
        f"info: guessed Qt docs dir {cache_qch} from the bootstrap Qt prefix "
        f"{prefix!r} ({cache}). Remember this location to skip the lookup next time.",
        file=sys.stderr,
    )
    return cache_qch, None


def find_qch_files(qch_dir):
    """Find all .qch files in the given directory."""
    pattern = os.path.join(qch_dir, "*.qch")
    return sorted(glob.glob(pattern))


def quncompress(data):
    """Decompress data compressed with Qt's qCompress (4-byte BE size header + zlib)."""
    if len(data) < 4:
        return b""
    expected_size = struct.unpack(">I", data[:4])[0]
    decompressed = zlib.decompress(data[4:])
    if len(decompressed) != expected_size:
        raise ValueError(
            f"Size mismatch: expected {expected_size}, got {len(decompressed)}"
        )
    return decompressed


class HTMLToText(html.parser.HTMLParser):
    """Convert HTML to readable plain text with minimal formatting."""

    BLOCK_TAGS = {
        "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "tr", "br", "pre", "blockquote", "dt", "dd",
        "table", "thead", "tbody",
    }
    SKIP_TAGS = {"script", "style", "head", "nav"}
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    CODE_TAGS = {"code", "pre"}

    def __init__(self):
        super().__init__()
        self.result = []
        self.skip_depth = 0
        self.in_code = 0
        self.in_pre = 0
        self.current_tag = None
        self.current_attrs = {}
        self.list_depth = 0
        self.in_td = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self.result.append("\n")
        if tag in self.HEADING_TAGS:
            self.result.append("\n## ")
        if tag == "li":
            self.result.append("  " * self.list_depth + "- ")
        if tag in ("ul", "ol"):
            self.list_depth += 1
        if tag == "code":
            self.in_code += 1
            if not self.in_pre:
                self.result.append("`")
        if tag == "pre":
            self.in_pre += 1
            self.result.append("\n```\n")
        if tag == "br":
            self.result.append("\n")
        if tag == "td" or tag == "th":
            self.in_td = True
            self.result.append(" | ")
        if tag == "a":
            pass  # we just keep the link text

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in self.HEADING_TAGS:
            self.result.append("\n")
        if tag in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
        if tag == "code":
            self.in_code = max(0, self.in_code - 1)
            if not self.in_pre:
                self.result.append("`")
        if tag == "pre":
            self.in_pre = max(0, self.in_pre - 1)
            self.result.append("\n```\n")
        if tag == "td" or tag == "th":
            self.in_td = False
        if tag in self.BLOCK_TAGS:
            self.result.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.in_pre:
            self.result.append(data)
        else:
            # Collapse whitespace
            text = re.sub(r"\s+", " ", data)
            self.result.append(text)

    def get_text(self):
        text = "".join(self.result)
        # Clean up excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_text(html_content):
    """Convert HTML string to readable plain text."""
    parser = HTMLToText()
    parser.feed(html_content)
    return parser.get_text()


def extract_section(html_content, anchor):
    """Extract a specific section from HTML by anchor ID.

    For member documentation, Qt uses <h3 id="anchor"> tags.
    We extract from the anchor to the next <h3> or end of parent.
    """
    if not anchor:
        return html_content

    # Try to find the anchor and extract the surrounding section
    # Qt doc format: <h3 class="fn" id="anchor-name">...</h3> followed by description
    patterns = [
        # h3 with id attribute
        rf'<h3[^>]*\bid\s*=\s*["\']?{re.escape(anchor)}["\']?[^>]*>',
        # Any element with id/name attribute matching anchor
        rf'<[^>]*\b(?:id|name)\s*=\s*["\']?{re.escape(anchor)}["\']?[^>]*>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            start = match.start()
            # Find the next h3 or h2 after this section
            next_heading = re.search(
                r"<h[23][^>]*>", html_content[match.end():]
            )
            if next_heading:
                end = match.end() + next_heading.start()
            else:
                # Take until end of the main content div or a reasonable amount
                end = min(len(html_content), start + 10000)
            return html_content[start:end]

    return None


def search_symbols(query, qch_dir=DEFAULT_QCH_DIR, limit=50):
    """Search for symbols matching the query across all .qch files."""
    qch_files = find_qch_files(qch_dir)
    if not qch_files:
        print(f"No .qch files found in {qch_dir}", file=sys.stderr)
        return []

    results = []
    query_lower = query.lower()

    for qch_file in qch_files:
        module = os.path.splitext(os.path.basename(qch_file))[0]
        try:
            db = sqlite3.connect(f"file:{qch_file}?mode=ro", uri=True)
            # Use LIKE for case-insensitive substring match
            rows = db.execute(
                """
                SELECT DISTINCT i.Name, i.Identifier, i.Anchor, fn.Name as FileName, fn.Title
                FROM IndexTable i
                LEFT JOIN FileNameTable fn ON fn.FileId = i.FileId
                WHERE i.Name LIKE ? OR i.Identifier LIKE ?
                ORDER BY
                    CASE
                        WHEN i.Name = ? THEN 0
                        WHEN i.Identifier = ? THEN 1
                        WHEN i.Name LIKE ? THEN 2
                        ELSE 3
                    END,
                    length(i.Name)
                LIMIT ?
                """,
                (
                    f"%{query}%", f"%{query}%",
                    query, query,
                    f"{query}%",
                    limit,
                ),
            ).fetchall()
            db.close()

            for name, identifier, anchor, filename, title in rows:
                results.append({
                    "name": name,
                    "identifier": identifier or name,
                    "anchor": anchor or "",
                    "filename": filename or "",
                    "title": title or "",
                    "module": module,
                })
        except sqlite3.Error as e:
            print(f"Warning: error reading {qch_file}: {e}", file=sys.stderr)

    # De-duplicate and sort
    seen = set()
    unique = []
    for r in results:
        key = (r["identifier"], r["anchor"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Sort: exact match first, then prefix match, then by length
    def sort_key(r):
        name = r["name"].lower()
        ident = r["identifier"].lower()
        if name == query_lower or ident == query_lower:
            return (0, len(name))
        if name.startswith(query_lower) or ident.startswith(query_lower):
            return (1, len(name))
        return (2, len(name))

    unique.sort(key=sort_key)
    return unique[:limit]


def read_doc(symbol, qch_dir=DEFAULT_QCH_DIR, raw=False):
    """Read documentation for a symbol (class, method, enum, etc.).

    Symbol can be:
      - "QWidget" (class)
      - "QWidget::show" (member)
      - "QWidget::sizePolicy" (property/method)
    """
    qch_files = find_qch_files(qch_dir)
    if not qch_files:
        print(f"No .qch files found in {qch_dir}", file=sys.stderr)
        return None

    # Parse the symbol to determine class vs member
    parts = symbol.split("::")
    class_name = parts[0]
    member_name = parts[1] if len(parts) > 1 else None

    # Search for the symbol in all .qch files
    best_match = None

    for qch_file in qch_files:
        try:
            db = sqlite3.connect(f"file:{qch_file}?mode=ro", uri=True)

            if member_name:
                # Look for specific member
                rows = db.execute(
                    """
                    SELECT i.Name, i.Identifier, i.Anchor, i.FileId, fn.Name, fn.Title
                    FROM IndexTable i
                    LEFT JOIN FileNameTable fn ON fn.FileId = i.FileId
                    WHERE (i.Identifier = ? OR i.Identifier LIKE ?)
                    ORDER BY
                        CASE WHEN i.Identifier = ? THEN 0 ELSE 1 END
                    LIMIT 5
                    """,
                    (symbol, f"{symbol}%", symbol),
                ).fetchall()
            else:
                # Look for class
                rows = db.execute(
                    """
                    SELECT i.Name, i.Identifier, i.Anchor, i.FileId, fn.Name, fn.Title
                    FROM IndexTable i
                    LEFT JOIN FileNameTable fn ON fn.FileId = i.FileId
                    WHERE i.Name = ? AND (i.Anchor = '' OR i.Anchor IS NULL)
                    LIMIT 5
                    """,
                    (class_name,),
                ).fetchall()

            if not rows:
                db.close()
                continue

            # Take the best match
            name, identifier, anchor, file_id, filename, title = rows[0]

            # Fetch the HTML content
            data_row = db.execute(
                "SELECT Data FROM FileDataTable WHERE Id = ?", (file_id,)
            ).fetchone()
            db.close()

            if data_row and data_row[0]:
                best_match = {
                    "name": name,
                    "identifier": identifier,
                    "anchor": anchor,
                    "filename": filename,
                    "title": title,
                    "data": data_row[0],
                    "module": os.path.splitext(os.path.basename(qch_file))[0],
                }
                break

        except sqlite3.Error as e:
            print(f"Warning: error reading {qch_file}: {e}", file=sys.stderr)

    if not best_match:
        print(f"No documentation found for '{symbol}'", file=sys.stderr)
        return None

    # Decompress
    html_content = quncompress(best_match["data"]).decode("utf-8", errors="replace")

    # Extract section if anchor specified
    anchor = best_match["anchor"] or (member_name.lower() if member_name else None)
    if anchor:
        section = extract_section(html_content, anchor)
        if section:
            html_content = section
        else:
            # Try common anchor patterns Qt uses
            for alt_anchor in [
                anchor,
                anchor.replace(" ", "-"),
                f"{anchor}-prop",
                f"{anchor}-signal",
            ]:
                section = extract_section(html_content, alt_anchor)
                if section:
                    html_content = section
                    break

    if raw:
        return html_content

    text = html_to_text(html_content)

    # Add header
    header = f"# {best_match['identifier'] or best_match['name']}"
    if best_match["title"]:
        header += f"\nFrom: {best_match['title']}"
    header += f"\nModule: {best_match['module']}"

    return f"{header}\n\n{text}"


def read_page(filename, qch_dir=DEFAULT_QCH_DIR, raw=False):
    """Read a documentation page by its HTML filename (e.g., 'qwidget.html')."""
    qch_files = find_qch_files(qch_dir)
    if not qch_files:
        print(f"No .qch files found in {qch_dir}", file=sys.stderr)
        return None

    for qch_file in qch_files:
        try:
            db = sqlite3.connect(f"file:{qch_file}?mode=ro", uri=True)
            row = db.execute(
                """
                SELECT fn.Title, fd.Data
                FROM FileNameTable fn
                JOIN FileDataTable fd ON fd.Id = fn.FileId
                WHERE fn.Name LIKE ?
                LIMIT 1
                """,
                (f"%{filename}%",),
            ).fetchone()
            db.close()

            if row:
                title, data = row
                html_content = quncompress(data).decode("utf-8", errors="replace")
                if raw:
                    return html_content
                text = html_to_text(html_content)
                module = os.path.splitext(os.path.basename(qch_file))[0]
                return f"# {title}\nModule: {module}\n\n{text}"

        except sqlite3.Error as e:
            print(f"Warning: error reading {qch_file}: {e}", file=sys.stderr)

    print(f"No page found matching '{filename}'", file=sys.stderr)
    return None


def list_modules(qch_dir=DEFAULT_QCH_DIR):
    """List all available .qch modules."""
    qch_files = find_qch_files(qch_dir)
    if not qch_files:
        print(f"No .qch files found in {qch_dir}", file=sys.stderr)
        return

    print(f"Qt documentation modules in {qch_dir}:\n")
    for qch_file in qch_files:
        name = os.path.splitext(os.path.basename(qch_file))[0]
        try:
            db = sqlite3.connect(f"file:{qch_file}?mode=ro", uri=True)
            count = db.execute("SELECT COUNT(*) FROM IndexTable").fetchone()[0]
            ns = db.execute("SELECT Name FROM NamespaceTable LIMIT 1").fetchone()
            db.close()
            ns_name = ns[0] if ns else "?"
            print(f"  {name:40s} ({count:5d} symbols)  [{ns_name}]")
        except sqlite3.Error:
            print(f"  {name:40s} (error reading)")


def main():
    parser = argparse.ArgumentParser(
        description="Read Qt documentation from local .qch files"
    )
    parser.add_argument(
        "--qch-dir",
        default=DEFAULT_QCH_DIR,
        help="Directory containing .qch files. Optional: defaults to QT_QCH_DIR, "
        "else auto-derived from the bootstrap Qt-prefix cache "
        f"({BOOTSTRAP_QT_PREFIX_CACHE}).",
    )
    subparsers = parser.add_subparsers(dest="command")

    # search
    sp_search = subparsers.add_parser("search", help="Search for symbols")
    sp_search.add_argument("query", help="Symbol name to search for")
    sp_search.add_argument(
        "-n", "--limit", type=int, default=30, help="Max results (default: 30)"
    )

    # read
    sp_read = subparsers.add_parser("read", help="Read documentation for a symbol")
    sp_read.add_argument(
        "symbol", help="Symbol to look up (e.g., QWidget, QWidget::show)"
    )
    sp_read.add_argument(
        "--raw", action="store_true", help="Output raw HTML"
    )

    # page
    sp_page = subparsers.add_parser("page", help="Read a doc page by filename")
    sp_page.add_argument("filename", help="HTML filename (e.g., qwidget.html)")
    sp_page.add_argument(
        "--raw", action="store_true", help="Output raw HTML"
    )

    # list
    subparsers.add_parser("list", help="List available modules")

    args = parser.parse_args()

    # No subcommand: show help. Resolve the docs dir only once we know a command
    # actually needs it — otherwise a missing bootstrap cache would error out
    # `qtdoc.py` with no args instead of printing usage.
    if not args.command:
        parser.print_help()
        return

    qch_dir, err = resolve_qch_dir(args.qch_dir)
    if err:
        parser.error(err)
    args.qch_dir = qch_dir

    if args.command == "search":
        results = search_symbols(args.query, args.qch_dir, args.limit)
        if not results:
            print("No results found.")
            return
        # Format output
        print(f"Found {len(results)} result(s) for '{args.query}':\n")
        for r in results:
            anchor_info = f"#{r['anchor']}" if r["anchor"] else ""
            print(f"  {r['identifier']:55s} [{r['module']}] {r['filename']}{anchor_info}")

    elif args.command == "read":
        doc = read_doc(args.symbol, args.qch_dir, args.raw)
        if doc:
            print(doc)

    elif args.command == "page":
        doc = read_page(args.filename, args.qch_dir, args.raw)
        if doc:
            print(doc)

    elif args.command == "list":
        list_modules(args.qch_dir)


if __name__ == "__main__":
    main()
