#!/usr/bin/env python3
"""Export the OpenAPI schema to docs/openapi.json."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

with patch("src.api.main.init_services"), patch("src.api.main.shutdown_services"):
    from src.api.main import create_app

    app = create_app()

schema = app.openapi()
output = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(schema, indent=2) + "\n")
print(f"Exported {len(schema['paths'])} paths to {output}")
