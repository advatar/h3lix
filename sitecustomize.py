"""
Local sitecustomize to disable external pytest autoloaded plugins that may be
present in the user environment (e.g., pytest-vcr + httpx incompatibility).
"""
import os

# Prevent third-party plugins outside this repo from breaking pytest discovery.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
