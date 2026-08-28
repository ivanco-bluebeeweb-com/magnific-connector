"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension instance
-- same pattern as Klaviyo Connector's main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "models", "magnific_client", "model_registry", "accounts",
    "handlers_generation", "handlers_editing", "handlers_audio",
    "handlers_stock", "handlers_analytics",
    "panels", "panels_center", "panels_settings",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import accounts  # noqa: E402,F401
import handlers_generation  # noqa: E402,F401
import handlers_editing  # noqa: E402,F401
import handlers_audio  # noqa: E402,F401
import handlers_stock  # noqa: E402,F401
import handlers_analytics  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_center  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
