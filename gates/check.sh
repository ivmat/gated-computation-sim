#!/bin/sh
# Minimum viable check suite for this repo. Self-contained: only depends on a
# POSIX shell and python3 (stdlib only). Safe to run from any working
# directory; it cd's into the repo root (or the path given as $1) first.
#
# Checks:
#   (a) syntax floor    - `python3 -m py_compile` every tracked .py file
#   (b) test suite       - not present in this repo (no tests/ dir, no pytest
#                           config) as of when this gate was added. If a fast
#                           (<~60s) pytest suite is added later, wire it in
#                           here and run it before the other checks.
#   (c) doc links         - every relative markdown link resolves to a real
#                           file in the repo
#   (d) secret scan       - flag key/token-shaped strings in tracked files
#   (e) file size          - refuse any tracked file over 20MB
#
# Exit 0 and prints "check.sh: PASS" only if every check passes.

set -eu

root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$root"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT INT TERM

fail=0

echo "== check.sh: running in $root =="

# List tracked files once; fall back to `find` if not a git checkout.
if git rev-parse --git-dir >/dev/null 2>&1; then
  git ls-files >"$tmpdir/tracked.txt"
else
  find . -type f -not -path './.git/*' | sed 's#^\./##' >"$tmpdir/tracked.txt"
fi

# --- (a) syntax floor ---------------------------------------------------
echo "-- py_compile --"
grep -E '\.py$' "$tmpdir/tracked.txt" >"$tmpdir/py_files.txt" || true
if [ -s "$tmpdir/py_files.txt" ]; then
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    if ! python3 -m py_compile "$f"; then
      echo "SYNTAX ERROR: $f"
      fail=1
    fi
  done <"$tmpdir/py_files.txt"
else
  echo "(no .py files)"
fi

# --- (b) test suite -------------------------------------------------------
# Intentionally not run: no tests/ directory or pytest entrypoint exists in
# this repo. See header comment.

# --- (c) markdown relative links resolve ----------------------------------
echo "-- markdown link check --"
grep -E '\.md$' "$tmpdir/tracked.txt" >"$tmpdir/md_files.txt" || true
if [ -s "$tmpdir/md_files.txt" ]; then
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    if ! python3 - "$f" <<'PYEOF'
import re, sys, os

path = sys.argv[1]
base = os.path.dirname(path)
text = open(path, encoding="utf-8").read()
bad = []
for m in re.finditer(r"\]\(([^)]+)\)", text):
    target = m.group(1).strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        continue
    target = target.split("#", 1)[0].strip()
    if not target or target.startswith("/"):
        continue
    candidate = os.path.normpath(os.path.join(base, target))
    if not os.path.exists(candidate):
        bad.append(target)
if bad:
    print(f"BROKEN LINKS in {path}: {bad}")
    sys.exit(1)
PYEOF
    then
      fail=1
    fi
  done <"$tmpdir/md_files.txt"
else
  echo "(no .md files)"
fi

# --- (d) secret scan -------------------------------------------------------
echo "-- secret scan --"
if ! python3 - "$tmpdir/tracked.txt" <<'PYEOF'
import os, re, sys

patterns = [
    re.compile(r"AKIA[0-9A-Z]{16}"),                    # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM private key
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                 # provider-style "sk-" secret key
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),                # GitHub PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),        # Slack token
    re.compile(
        r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*'
        r'["\'][A-Za-z0-9/_+=-]{16,}["\']'
    ),
]

listfile = sys.argv[1]
with open(listfile, encoding="utf-8") as fh:
    files = [line.rstrip("\n") for line in fh if line.strip()]

bad = False
for f in files:
    if not os.path.isfile(f):
        continue
    try:
        data = open(f, "rb").read()
    except OSError:
        continue
    if b"\0" in data[:8000]:
        continue  # skip binaries
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        continue
    for pat in patterns:
        m = pat.search(text)
        if m:
            print(f"POSSIBLE SECRET in {f}: matched {pat.pattern!r}")
            bad = True

sys.exit(1 if bad else 0)
PYEOF
then
  fail=1
fi

# --- (e) refuse oversized files ---------------------------------------------
echo "-- file size check (limit 20MB) --"
if ! python3 - "$tmpdir/tracked.txt" <<'PYEOF'
import os, sys

limit = 20 * 1024 * 1024
listfile = sys.argv[1]
with open(listfile, encoding="utf-8") as fh:
    files = [line.rstrip("\n") for line in fh if line.strip()]

bad = False
for f in files:
    if not os.path.isfile(f):
        continue
    sz = os.path.getsize(f)
    if sz > limit:
        print(f"OVERSIZED FILE: {f} ({sz} bytes > {limit})")
        bad = True

sys.exit(1 if bad else 0)
PYEOF
then
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "check.sh: FAIL"
  exit 1
fi
echo "check.sh: PASS"
exit 0
