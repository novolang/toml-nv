#!/usr/bin/env bash
# tests/toml_test.sh — the whole TOML 1.0.0 part of the toml-test
# corpus, run against this package.
#
# toml-test (https://github.com/toml-lang/toml-test) is the reference
# corpus for TOML parsers.  This builds `tests/toml_test_harness.nv`
# against the package's sources and hands it every document of the
# corpus's `files-toml-1.0.0` list; `tests/toml_test.py` checks each
# answer against the upstream expectation and the round trips.
#
# `tests/vectors_tests.nv` holds the same documents as an ordinary
# suite; this script compares with the upstream JSON files themselves.
#
# Run from anywhere:  bash tests/toml_test.sh [path-to-toml-test-checkout]
# Without a path, the corpus is cloned into a temporary directory.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="$(cd "$HERE/.." && pwd)"
NOVO="${NOVO:-$HOME/.novo/bin/novo}"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/toml-nv-toml-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

CORPUS="${1:-}"
if [ -z "$CORPUS" ]; then
  CORPUS="$WORK/toml-test"
  git clone --quiet --depth 1 https://github.com/toml-lang/toml-test "$CORPUS" || {
    echo "  ✗ could not clone toml-test; pass a checkout as the first argument"
    exit 1
  }
fi

# A package of its own: this package's sources, the harness as its
# `main`, and this package's manifest and lock so the dependencies
# resolve the same way.
mkdir -p "$WORK/pkg/src"
cp "$PKG"/src/*.nv "$WORK/pkg/src/"
cp "$HERE/toml_test_harness.nv" "$WORK/pkg/src/harness.nv"
cp "$PKG/novo.lock" "$WORK/pkg/"
sed -e 's/^name        = "toml-nv"/name        = "tomltestharness"\nmain        = "src\/harness.nv"/' \
  "$PKG/novo.toml" > "$WORK/pkg/novo.toml"
( cd "$WORK/pkg" && NOVO_LEAK_CHECK=0 timeout 900 "$NOVO" build src/harness.nv -o harness ) \
  > "$WORK/build.log" 2>&1 || {
  echo "  ✗ the harness did not build; see below"
  grep -E 'error' "$WORK/build.log" | head -5
  exit 1
}
python3 "$HERE/toml_test.py" "$WORK/pkg/harness" "$CORPUS"
