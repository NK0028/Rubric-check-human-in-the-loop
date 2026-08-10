#!/usr/bin/env zsh
# Adds the installed uv location to zsh's PATH, then verifies it.
set -euo pipefail

uv_bin_dir="$HOME/.local/bin"
path_export='export PATH="$HOME/.local/bin:$PATH"'

if [[ ! -x "$uv_bin_dir/uv" ]]; then
  echo "uv was not found at $uv_bin_dir/uv. Install it first: https://docs.astral.sh/uv/"
  exit 1
fi

touch "$HOME/.zshrc"
if ! grep -Fqx "$path_export" "$HOME/.zshrc"; then
  printf '\n# uv package manager\n%s\n' "$path_export" >> "$HOME/.zshrc"
fi

export PATH="$uv_bin_dir:$PATH"
uv --version
echo "Done. Open a new terminal, or run: source ~/.zshrc"
