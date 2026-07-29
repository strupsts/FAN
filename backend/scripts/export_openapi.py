from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "openapi" / "openapi.json"


def export_openapi(output_path: Path = OUTPUT_PATH) -> None:
    app = create_app()
    schema: dict[str, Any] = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"OpenAPI schema written to: {output_path}")
    print(f"API title: {schema['info']['title']}")
    print(f"Paths exported: {len(schema.get('paths', {}))}")


def main() -> None:
    export_openapi()


if __name__ == "__main__":
    main()
