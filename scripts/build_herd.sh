#!/usr/bin/env bash
# Rebuild the pinned public tool; compiler dependencies must already exist.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERD_SOURCE_DIR="${HERD_BUILD_DIR:-$PROJECT_ROOT/.build/herdtools7}"
HERD_COMMIT=1ca343e16a2038e406d1ac674e7e3a1b722b36c7
for tool in git ocamlc dune menhir; do
  command -v "$tool" >/dev/null || { echo "Missing $tool. Install OCaml, dune, menhir, zarith (see docs/HERD.md)." >&2; exit 1; }
done
if [ ! -d "$HERD_SOURCE_DIR/.git" ]; then
  mkdir -p "$(dirname "$HERD_SOURCE_DIR")"
  git clone https://github.com/herd/herdtools7.git "$HERD_SOURCE_DIR"
fi
git -C "$HERD_SOURCE_DIR" checkout --detach "$HERD_COMMIT"
cd "$HERD_SOURCE_DIR"
sh version-gen.sh "$PROJECT_ROOT/vendor/herdtools7"
dune build -j "${HERD_BUILD_JOBS:-2}" --profile release herd/herd.exe
mkdir -p "$PROJECT_ROOT/vendor/herdtools7/bin" "$PROJECT_ROOT/vendor/herdtools7/herd/libdir"
cp _build/default/herd/herd.exe "$PROJECT_ROOT/vendor/herdtools7/bin/herd7"
chmod u+w "$PROJECT_ROOT/vendor/herdtools7/bin/herd7"
command -v strip >/dev/null && strip "$PROJECT_ROOT/vendor/herdtools7/bin/herd7"
cp -a herd/libdir/. "$PROJECT_ROOT/vendor/herdtools7/herd/libdir/"
cp LICENSE.txt "$PROJECT_ROOT/vendor/herdtools7/LICENSE.txt"
printf 'herdtools7 7.58\nhttps://github.com/herd/herdtools7\ncommit %s\n' "$HERD_COMMIT" > "$PROJECT_ROOT/vendor/herdtools7/REVISION"
"$PROJECT_ROOT/vendor/herdtools7/bin/herd7" -version
