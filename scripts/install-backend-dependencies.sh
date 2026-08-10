#!/usr/bin/env zsh
# Installs the backend packages required for the current RubriCheck AI milestone.
set -euo pipefail

cd "$(dirname "$0")/../backend"
uv add sqlalchemy
