#!/bin/sh
# Install the repo's git hooks into .git/hooks. Idempotent: safe to run
# repeatedly. Chains any pre-existing pre-push hook (e.g. one installed by
# local tooling) as pre-push.pre-guard so it still runs; every other hook
# is left untouched.

set -eu

repo_root=$(git rev-parse --show-toplevel)
hooks_dir=$(git rev-parse --git-path hooks)
cd "$repo_root"

mkdir -p "$hooks_dir"

# If a pre-push hook is already installed and it isn't ours, preserve it as
# pre-push.pre-guard so our hook can chain to it.
if [ -f "$hooks_dir/pre-push" ] && ! grep -q 'gates/check.sh' "$hooks_dir/pre-push" 2>/dev/null; then
  cp "$hooks_dir/pre-push" "$hooks_dir/pre-push.pre-guard"
  chmod +x "$hooks_dir/pre-push.pre-guard"
  echo "install_hooks.sh: preserved existing pre-push as pre-push.pre-guard"
fi

cp "gates/pre-push" "$hooks_dir/pre-push"
chmod +x "$hooks_dir/pre-push"
echo "install_hooks.sh: installed $hooks_dir/pre-push"

exit 0
