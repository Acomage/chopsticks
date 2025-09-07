from __future__ import annotations

import os
from pathlib import Path

REPO_DIR = Path("~/.config/chopsticks/repo/").expanduser().resolve()

# State file path (installed packages)
STATE_FILE = Path("~/.config/chopsticks/state.json").expanduser().resolve()

# Runtime behavior
DRY_RUN = bool(int(os.environ.get("CONFIGMGR_DRY_RUN", "0")))

# Command execution defaults
SHELL_ENV = os.environ.copy()

