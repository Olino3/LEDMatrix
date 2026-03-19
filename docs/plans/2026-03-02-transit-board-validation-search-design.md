# Design: Transit Board Config Validation Fix + Station Search

**Date:** 2026-03-02
**Scope:** transit-board plugin + `web_interface/blueprints/api_v3.py`

---

## Problem 1: Config Validation Failure for Numeric-Looking `station_id`

### Root Cause
`_parse_form_value_with_schema()` in `api_v3.py` has a fallback that converts any numeric-looking string to an integer/float (lines 3686–3692), regardless of the field's schema type. When a user enters `"65"` as a station ID, it becomes integer `65`, which fails the `"type": "string"` schema check. `"B18"` works because it can't be parsed as a number.

This is a core web API bug, not transit-board specific.

### Fix
Guard the fallback number parsing with a schema type check:

```python
# Only attempt numeric coercion if schema does NOT say type: "string"
if not (prop and prop.get('type') == 'string'):
    try:
        if '.' in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        pass
```

**Impact:** Any plugin with a string field whose value looks like a number (e.g., `"65"`, `"007"`, `"42abc"`) will now save correctly.

---

## Problem 2: No Way to Search for Station IDs

### Approach: `web_ui_actions` Search Script

Add a `search_stations` action to the transit-board manifest, backed by a Python script that queries the stops DB. The existing `execute_plugin_action` endpoint (`POST /api/v3/plugins/action`) dispatches to this script.

### Components

**`manifest.json`** — add `web_ui_actions`:
```json
"web_ui_actions": [
  {
    "id": "search_stations",
    "label": "Search Stations",
    "description": "Find a station by name to get its GTFS Stop ID",
    "type": "script",
    "script": "scripts/search_stations.py",
    "input": {
      "type": "text",
      "placeholder": "e.g. Times Square, 79 St, Atlantic Av",
      "param": "query"
    }
  }
]
```

**`scripts/search_stations.py`** — action handler:
- Accepts `params["query"]` (station name search string)
- Locates the stops DB at the same path the plugin uses (`{cache_dir}/transit_stops_mta.db`)
- Calls `StopsDatabase.search(query, limit=10)`
- Returns a formatted table: `GTFS ID | Station Name | Routes | Northbound | Southbound`
- If DB is empty, returns a message instructing the user to enable the plugin first

**Script interface** — the `execute_plugin_action` endpoint loads the script module and calls a standard entry-point function. Script must expose a callable that accepts `(params, plugin_dir, ledmatrix_root)` and returns `{"status": "success", "result": <str>}`.

### Data Flow
```
User clicks "Search Stations" in web UI
  → types query in input modal
  → POST /api/v3/plugins/action {plugin_id, action_id: "search_stations", params: {query: "79 St"}}
  → execute_plugin_action loads scripts/search_stations.py
  → script queries transit_stops_mta.db
  → returns formatted station list
  → web UI displays result; user copies GTFS Stop ID into station_id field
```

### Result Format (example)
```
GTFS ID  Station Name              Routes  Northbound   Southbound
-------  ------------------------  ------  -----------  -------------
B18      79 St (West End)          D       Manhattan    Coney Island
R28      79 St                     1       Uptown       Downtown
```

---

## Files to Change

| File | Change |
|------|--------|
| `web_interface/blueprints/api_v3.py` | Guard fallback number coercion in `_parse_form_value_with_schema` |
| `plugin-repos/transit-board/manifest.json` | Add `web_ui_actions` with `search_stations` entry |
| `plugin-repos/transit-board/scripts/search_stations.py` | New file: action script |

---

## Out of Scope
- Inline autocomplete on the `station_id` field (requires web UI template changes)
- CLI station search command
- Multi-agency search (only MTA stops DB for now)
