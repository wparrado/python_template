#!/usr/bin/env bash
# Guard: prevent any modification to the architectural test files.
#
# Architecture tests encode the dependency rules of the project.
# They are the enforceable contract between all contributors.
# Changes require an explicit, reviewed pull request — they must
# never happen as a side-effect of a regular feature commit.

set -euo pipefail

ARCH_DIR="tests/architecture"

staged_arch_files=$(git diff --cached --name-only | grep "^${ARCH_DIR}/" || true)

if [ -z "$staged_arch_files" ]; then
    exit 0
fi

echo ""
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║  BLOCKED: architectural test files must not be modified.    ║"
echo "  ║                                                              ║"
echo "  ║  Architecture tests are the dependency contract of this     ║"
echo "  ║  project. Changing them requires explicit team review.      ║"
echo "  ║                                                              ║"
echo "  ║  Staged protected files:                                     ║"
while IFS= read -r file; do
    printf  "  ║    • %-56s║\n" "$file"
done <<< "$staged_arch_files"
echo "  ║                                                              ║"
echo "  ║  To proceed: open a PR, get approval, then bypass with:     ║"
echo "  ║    git commit --no-verify  (only with explicit approval)    ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo ""

exit 1
