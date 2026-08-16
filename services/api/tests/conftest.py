"""Keep API unit tests isolated from the durable integration runtime."""

from __future__ import annotations

import os

os.environ["WORKFLOW_STORE_MODE"] = "memory"
