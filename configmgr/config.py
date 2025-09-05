from __future__ import annotations

import os
from pathlib import Path

# Directory where packages (the external repo with pkg.py) are located.
# By default, use "<cwd>/repo" to match the example.
REPO_DIR = Path(os.environ.get("CONFIGMGR_REPO", Path.cwd() / "repo")).resolve()

# State file path (installed packages)
STATE_FILE = Path(os.environ.get("CONFIGMGR_STATE", Path.cwd() / ".configmgr_state.json")).resolve()

# Runtime behavior
DRY_RUN = bool(int(os.environ.get("CONFIGMGR_DRY_RUN", "0")))

# Command execution defaults
SHELL_ENV = os.environ.copy()