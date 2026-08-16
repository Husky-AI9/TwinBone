"""Export the FastAPI schema used to generate/check the TypeScript client."""

from __future__ import annotations

import json
from pathlib import Path

from services.api.app.main import app


def main() -> None:
    destination = Path("packages/api-client/openapi.json")
    destination.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
