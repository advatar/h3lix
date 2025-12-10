#!/usr/bin/env bash
set -euo pipefail

# Disable external pytest auto-loaded plugins (e.g., pytest-vcr with incompatible httpx)
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

python3 -m pytest "$@"
