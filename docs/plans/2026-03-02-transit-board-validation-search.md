# Transit Board: Validation Fix + Station Search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix a web API bug that coerces numeric-looking strings to integers (breaking `station_id: "65"`), and add a station search action to the transit-board plugin.

**Architecture:** Two independent changes — (1) a one-line guard in `_parse_form_value_with_schema` in the core web API, (2) a new `search_stations.py` action script in the transit-board plugin, registered via `web_ui_actions` in its manifest.

**Tech Stack:** Python 3, Flask, jsonschema, SQLite (stops DB), existing `web_ui_actions` dispatch mechanism in `api_v3.py`.

---

## Background

### Script execution mechanism (web_ui_actions)

When a plugin action of `type: "script"` is invoked via `POST /api/v3/plugins/action`:
1. `action_params` dict is serialized to JSON and written to the subprocess's stdin
2. The script reads stdin: `params = json.loads(sys.stdin.read())`
3. Script writes JSON to stdout; if valid JSON, it's returned directly as the HTTP response
4. Response shape: `{"status": "success", "message": "...", "results": [...]}`

### Stops DB location

`TransitBoardPlugin._db_path()` uses `cache_manager.get_cache_dir()` which resolves to:
- Production/Pi: `/var/cache/ledmatrix/`
- Dev fallback: `~/.ledmatrix_cache/`

The file is named `transit_stops_{agency_id}.db` (e.g., `transit_stops_mta.db`).

The search script must find this path without access to `cache_manager` — it checks known locations in order.

### Test commands

```bash
# All transit-board tests
cd /root/LEDMatrix/plugin-repos/transit-board
/root/LEDMatrix/.venv/bin/pytest test/ -q

# Single test
/root/LEDMatrix/.venv/bin/pytest test/test_search_stations.py -v

# Web API tests (LEDMatrix core)
cd /root/LEDMatrix
EMULATOR=true .venv/bin/pytest test/test_web_api.py -v --override-ini="addopts=" 2>/dev/null || \
EMULATOR=true .venv/bin/pytest test/ -k "form_value or parse_form" -v --override-ini="addopts="
```

---

## Task 1: Fix numeric-string coercion in `_parse_form_value_with_schema`

**Files:**
- Modify: `web_interface/blueprints/api_v3.py` (around line 3686)
- Test: `test/test_web_form_parsing.py` (new file)

### Step 1: Write the failing test

Create `test/test_web_form_parsing.py`:

```python
"""
Tests for _parse_form_value_with_schema in api_v3.py.

The function is module-level so we import it directly.
"""
import sys
import os

# Ensure LEDMatrix root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# api_v3 imports Flask app context — import the function via the module
# We monkey-patch just enough to let the import succeed.
os.environ.setdefault('EMULATOR', 'true')

from web_interface.blueprints.api_v3 import _parse_form_value_with_schema


STRING_SCHEMA = {
    "properties": {
        "station_id": {"type": "string", "default": ""}
    }
}

INTEGER_SCHEMA = {
    "properties": {
        "window_minutes": {"type": "integer", "default": 30}
    }
}


def test_numeric_string_stays_string_when_schema_says_string():
    """'65' must not be coerced to integer 65 when field type is string."""
    result = _parse_form_value_with_schema("65", "station_id", STRING_SCHEMA)
    assert result == "65", f"Expected '65' (str), got {result!r} ({type(result).__name__})"
    assert isinstance(result, str), f"Expected str, got {type(result).__name__}"


def test_alphanumeric_string_unchanged():
    """'B18' should pass through as-is."""
    result = _parse_form_value_with_schema("B18", "station_id", STRING_SCHEMA)
    assert result == "B18"


def test_empty_string_for_string_field():
    """Empty string is a valid value for an optional string field."""
    result = _parse_form_value_with_schema("", "station_id", STRING_SCHEMA)
    assert result == ""


def test_integer_field_still_coerced():
    """Integer fields should still be coerced from strings."""
    result = _parse_form_value_with_schema("30", "window_minutes", INTEGER_SCHEMA)
    assert result == 30
    assert isinstance(result, int)


def test_numeric_string_no_schema_coerced():
    """With no schema prop, numeric strings are still coerced (existing behaviour)."""
    result = _parse_form_value_with_schema("42", "unknown_field", {})
    assert result == 42
    assert isinstance(result, int)
```

### Step 2: Run the test to verify it fails

```bash
cd /root/LEDMatrix
EMULATOR=true .venv/bin/pytest test/test_web_form_parsing.py::test_numeric_string_stays_string_when_schema_says_string -v --override-ini="addopts="
```

Expected: **FAIL** — `AssertionError: Expected '65' (str), got 65 (int)`

### Step 3: Apply the fix

In `web_interface/blueprints/api_v3.py`, find the fallback number coercion block (around line 3686):

```python
        # Try parsing as number (fallback)
        try:
            if '.' in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            pass
```

Replace with:

```python
        # Try parsing as number (fallback) — skip when schema explicitly says string
        if not (prop and prop.get('type') == 'string'):
            try:
                if '.' in stripped:
                    return float(stripped)
                return int(stripped)
            except ValueError:
                pass
```

### Step 4: Run all new tests

```bash
cd /root/LEDMatrix
EMULATOR=true .venv/bin/pytest test/test_web_form_parsing.py -v --override-ini="addopts="
```

Expected: **5 PASSED**

### Step 5: Verify no regressions in the broader test suite

```bash
cd /root/LEDMatrix
EMULATOR=true .venv/bin/pytest test/ -q --override-ini="addopts=" --ignore=test/plugins 2>&1 | tail -5
```

Expected: same pass/fail counts as before (7 pre-existing failures unrelated to this change).

### Step 6: Commit

```bash
cd /root/LEDMatrix
git add web_interface/blueprints/api_v3.py test/test_web_form_parsing.py
git commit -m "fix(web): preserve string type for schema-typed string fields in form parsing

Numeric-looking strings like '65' were being coerced to integers by the
fallback number parsing in _parse_form_value_with_schema, causing JSON
schema validation to fail for fields declared as type: string.

Guard now skips fallback coercion when the schema property explicitly
declares type: string."
```

---

## Task 2: Write the station search script

**Files:**
- Create: `plugin-repos/transit-board/scripts/search_stations.py`
- Create: `plugin-repos/transit-board/scripts/__init__.py` (empty, makes it a package for imports)
- Test: `plugin-repos/transit-board/test/test_search_stations.py` (new file)

### Step 1: Write the failing test

Create `plugin-repos/transit-board/test/test_search_stations.py`:

```python
"""Tests for the search_stations action script."""
import json
import sqlite3
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add transit-board root to path
PLUGIN_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

import scripts.search_stations as search_mod


@pytest.fixture
def populated_db(tmp_path):
    """Create a stops DB with sample stations."""
    db_path = str(tmp_path / "transit_stops_mta.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE stops (
            stop_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            routes TEXT,
            north_label TEXT,
            south_label TEXT,
            lat REAL,
            lng REAL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.executemany(
        "INSERT INTO stops VALUES (?,?,?,?,?,?,?,datetime('now'))",
        [
            ("B18", "79 St", "D", "Manhattan", "Coney Island", 40.613501, -74.00061),
            ("R28", "79 St", "1", "Uptown", "Downtown", 40.784615, -73.979892),
            ("R16", "Times Sq-42 St", "N Q R W", "Uptown & Queens", "Downtown & Brooklyn", 40.7549, -73.9878),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def test_search_returns_matching_stations(populated_db):
    """Querying '79 St' returns both stations with that name."""
    results = search_mod.search_stops(populated_db, "79 St")
    assert len(results) == 2
    stop_ids = {r["stop_id"] for r in results}
    assert "B18" in stop_ids
    assert "R28" in stop_ids


def test_search_is_case_insensitive(populated_db):
    """Query is case-insensitive."""
    results = search_mod.search_stops(populated_db, "times sq")
    assert len(results) == 1
    assert results[0]["stop_id"] == "R16"


def test_search_partial_match(populated_db):
    """Partial station name matches."""
    results = search_mod.search_stops(populated_db, "Times")
    assert any(r["stop_id"] == "R16" for r in results)


def test_search_no_match_returns_empty(populated_db):
    """Non-matching query returns empty list."""
    results = search_mod.search_stops(populated_db, "ZZZNOMATCH")
    assert results == []


def test_format_results_table():
    """format_results returns a readable table string."""
    stations = [
        {"stop_id": "B18", "name": "79 St", "routes": "D",
         "north_label": "Manhattan", "south_label": "Coney Island"},
    ]
    output = search_mod.format_results(stations)
    assert "B18" in output
    assert "79 St" in output
    assert "Manhattan" in output


def test_run_outputs_json(populated_db, capsys):
    """run() reads params from stdin and prints JSON to stdout."""
    params = json.dumps({"query": "79 St"})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = params
        with patch.object(search_mod, "_find_db_path", return_value=populated_db):
            search_mod.run()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "success"
    assert "B18" in output["message"]


def test_run_handles_missing_db(capsys):
    """run() returns error JSON when DB doesn't exist yet."""
    params = json.dumps({"query": "anything"})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = params
        with patch.object(search_mod, "_find_db_path", return_value=None):
            search_mod.run()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "error"
    assert "bootstrap" in output["message"].lower() or "enable" in output["message"].lower()


def test_run_handles_empty_query(populated_db, capsys):
    """Empty query returns an informative error."""
    params = json.dumps({"query": ""})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = params
        with patch.object(search_mod, "_find_db_path", return_value=populated_db):
            search_mod.run()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == "error"
```

### Step 2: Run the test to verify it fails

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
/root/LEDMatrix/.venv/bin/pytest test/test_search_stations.py -v 2>&1 | head -20
```

Expected: **ERROR** — `ModuleNotFoundError: No module named 'scripts.search_stations'`

### Step 3: Create the scripts package and search script

Create `plugin-repos/transit-board/scripts/__init__.py` (empty file).

Create `plugin-repos/transit-board/scripts/search_stations.py`:

```python
"""
Station search action script for the transit-board plugin.

Invoked by the LEDMatrix web UI via execute_plugin_action.
Reads JSON params from stdin, queries the stops DB, writes JSON to stdout.

Input (stdin):  {"query": "station name"}
Output (stdout): {"status": "success"|"error", "message": "..."}
"""
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# DB location
# ---------------------------------------------------------------------------

_CANDIDATE_CACHE_DIRS = [
    "/var/cache/ledmatrix",
    os.path.expanduser("~/.ledmatrix_cache"),
]


def _find_db_path(agency_id: str = "mta") -> Optional[str]:
    """Return the first existing stops DB path, or None."""
    db_name = f"transit_stops_{agency_id}.db"
    for d in _CANDIDATE_CACHE_DIRS:
        candidate = os.path.join(d, db_name)
        if os.path.exists(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def search_stops(db_path: str, query: str, limit: int = 10) -> List[dict]:
    """Case-insensitive partial name search against the stops DB."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    pattern = f"%{query}%"
    rows = conn.execute(
        "SELECT stop_id, name, routes, north_label, south_label "
        "FROM stops WHERE name LIKE ? COLLATE NOCASE LIMIT ?",
        (pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_results(stations: List[dict]) -> str:
    """Return a human-readable table of search results."""
    if not stations:
        return "No stations found."

    col_id = max(len(s["stop_id"]) for s in stations)
    col_name = max(len(s["name"]) for s in stations)
    col_routes = max(len(s.get("routes") or "") for s in stations)

    col_id = max(col_id, 7)       # "GTFS ID"
    col_name = max(col_name, 12)  # "Station Name"
    col_routes = max(col_routes, 6)  # "Routes"

    header = (
        f"{'GTFS ID':<{col_id}}  {'Station Name':<{col_name}}  "
        f"{'Routes':<{col_routes}}  Northbound → Southbound"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for s in stations:
        north = s.get("north_label") or "—"
        south = s.get("south_label") or "—"
        lines.append(
            f"{s['stop_id']:<{col_id}}  {s['name']:<{col_name}}  "
            f"{(s.get('routes') or ''):<{col_routes}}  {north} → {south}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Read params from stdin, search, write JSON result to stdout."""
    raw = sys.stdin.read()
    try:
        params = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        params = {}

    query = (params.get("query") or "").strip()

    if not query:
        print(json.dumps({
            "status": "error",
            "message": "Enter a station name to search (e.g. '79 St', 'Times Square', 'Atlantic Av').",
        }))
        return

    db_path = _find_db_path()
    if not db_path:
        print(json.dumps({
            "status": "error",
            "message": (
                "Stops database not found. Enable the transit-board plugin and "
                "let it run once to bootstrap the station database, then try again."
            ),
        }))
        return

    stations = search_stops(db_path, query)

    if not stations:
        print(json.dumps({
            "status": "success",
            "message": f"No stations found matching '{query}'. Try a shorter or different search term.",
        }))
        return

    table = format_results(stations)
    print(json.dumps({
        "status": "success",
        "message": table,
    }))


if __name__ == "__main__":
    run()
```

### Step 4: Run the tests to verify they pass

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
/root/LEDMatrix/.venv/bin/pytest test/test_search_stations.py -v
```

Expected: **7 PASSED**

### Step 5: Run the full transit-board test suite to verify no regressions

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
/root/LEDMatrix/.venv/bin/pytest test/ -q
```

Expected: all tests that passed before still pass.

### Step 6: Commit

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
git add scripts/__init__.py scripts/search_stations.py test/test_search_stations.py
git commit -m "feat(search): add station search action script

Provides search_stops() and format_results() utilities backed by the
SQLite stops DB. Entry point run() reads JSON from stdin and writes
a formatted result table as JSON to stdout, compatible with the
execute_plugin_action dispatch mechanism."
```

---

## Task 3: Register the search action in the manifest

**Files:**
- Modify: `plugin-repos/transit-board/manifest.json`

### Step 1: Add `web_ui_actions` to the manifest

Open `plugin-repos/transit-board/manifest.json` and add the `web_ui_actions` key. The full updated file:

```json
{
  "id": "transit-board",
  "name": "Transit Board",
  "version": "0.2.1",
  "author": "Your Name",
  "description": "Displays real-time transit arrivals for a configured station using GTFS Realtime feeds. Compatible with NYC MTA, DC Metro, BART, Chicago L, and any GTFS-RT agency.",
  "entry_point": "manager.py",
  "class_name": "TransitBoardPlugin",
  "category": "transportation",
  "tags": ["transit", "subway", "bus", "gtfs", "arrivals", "mta", "realtime"],
  "display_modes": ["transit-board"],
  "update_interval": 30,
  "default_duration": 15,
  "web_ui_actions": [
    {
      "id": "search_stations",
      "label": "Search Stations",
      "description": "Find a station by name to get its GTFS Stop ID for the station_id field",
      "type": "script",
      "script": "scripts/search_stations.py",
      "input_label": "Station name",
      "input_placeholder": "e.g. Times Square, 79 St, Atlantic Av"
    }
  ]
}
```

Note: version bumped from `0.2.0` → `0.2.1`.

### Step 2: Verify the action is discoverable

The `execute_plugin_action` endpoint reads `manifest.json` and looks up `web_ui_actions` by `id`. Confirm the structure is correct:

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
python3 -c "
import json
m = json.load(open('manifest.json'))
actions = m.get('web_ui_actions', [])
action = next((a for a in actions if a['id'] == 'search_stations'), None)
assert action is not None, 'action not found'
assert action['type'] == 'script'
assert action['script'] == 'scripts/search_stations.py'
print('manifest OK:', action)
"
```

Expected: prints `manifest OK: {...}` with no assertion errors.

### Step 3: Smoke-test the script directly

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
echo '{"query": "Times"}' | /root/LEDMatrix/.venv/bin/python3 scripts/search_stations.py
```

Expected: JSON output — either a formatted station list (if stops DB exists) or the "Enable the plugin" error message (if DB doesn't exist yet). Both are correct; neither should be a Python traceback.

### Step 4: Commit

```bash
cd /root/LEDMatrix/plugin-repos/transit-board
git add manifest.json
git commit -m "feat(manifest): register search_stations web_ui_action

Exposes a Search Stations button in the web UI config page.
Users type a station name and receive a formatted table of GTFS Stop IDs
to copy into the station_id config field.

Version bumped to 0.2.1."
```

---

## Task 4: Commit the design docs

```bash
cd /root/LEDMatrix
git add docs/plans/2026-03-02-transit-board-validation-search-design.md \
        docs/plans/2026-03-02-transit-board-validation-search.md
git commit -m "docs: add transit-board validation fix and station search design + plan"
```

---

## How to use the station search from the web UI

After deploying:

1. Open the LEDMatrix web UI → plugin config for **Transit Board**
2. A **"Search Stations"** button appears (rendered by the `web_ui_actions` section)
3. Click it, type a station name (e.g. `"79 St"`, `"Times Square"`)
4. The result table shows matching stations with their **GTFS Stop ID** (e.g. `B18`), name, routes, and direction labels
5. Copy the GTFS Stop ID into the **`station_id`** field and save

If the DB hasn't been bootstrapped yet (plugin never ran), the search returns a message prompting you to enable the plugin first.
