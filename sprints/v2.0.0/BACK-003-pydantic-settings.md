# BACK-003 — Pydantic Settings and Config Models

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Done
**Phase:** v2.0.0 — Backend Modernization
**Type:** Feat
**Depends on:** [BACK-001](BACK-001-fastapi-app-scaffold.md)
**Blocks:** [BACK-005](BACK-005-api-routes-system.md), [BACK-006](BACK-006-api-routes-plugins.md)

---

## Context

The project has three overlapping config classes: `ConfigManager` (663 LOC), `ConfigService` (452 LOC), and `ConfigManagerAtomic` (533 LOC). Per the architecture guardrail, all three coexist until Phase 7. This ticket does NOT remove or replace them. Instead, it creates typed Pydantic models for config sections that FastAPI routes will use for request/response validation, and a `pydantic-settings` class for application-level settings (port, host, debug, secrets path).

Plugin configs must continue to be delivered as plain `dict` to plugins (not Pydantic model instances) to avoid breaking all 28 plugins.

---

## Acceptance Criteria

- [ ] `src/api/config.py` defines `AppSettings(BaseSettings)` with env var overrides for host, port, debug, log format
- [ ] `src/api/models/` package contains Pydantic response/request models for config endpoints
- [ ] `SystemConfigModel` covers display, schedule, and general settings sections
- [ ] `PluginConfigModel` validates plugin config against schema but serializes to plain `dict`
- [ ] `SecretStoreModel` wraps secret access (file-backed, reads `config/config_secrets.json`)
- [ ] All models include `model_config = ConfigDict(from_attributes=True)` for ORM-mode compat
- [ ] Env var prefix is `LEDMATRIX_` (e.g., `LEDMATRIX_PORT=5000`)
- [ ] Existing `ConfigManager` is NOT modified or removed

---

## Implementation Checklist

### 1. Create `src/api/config.py` — Application Settings

- [ ] Define `AppSettings(BaseSettings)` with fields:
  - `host: str = "0.0.0.0"`
  - `port: int = 5000`
  - `debug: bool = False`
  - `json_logging: bool = False`
  - `hot_reload: bool = False`
  - `config_path: str = "config/config.json"`
  - `secrets_path: str = "config/config_secrets.json"`
- [ ] Use `model_config = SettingsConfigDict(env_prefix="LEDMATRIX_")`
- [ ] Add factory function `get_settings()` with `@lru_cache`

### 2. Create `src/api/models/` package

- [ ] Create `src/api/models/__init__.py`
- [ ] Create `src/api/models/config.py` with:
  - `DisplayHardwareConfig` (cols, rows, chain_length, parallel, brightness, etc.)
  - `ScheduleConfig` (enabled, on_time, off_time, dim settings)
  - `SystemConfigResponse` (full system config as a response model)
  - `ConfigUpdateRequest` (partial update with optional fields)
- [ ] Create `src/api/models/common.py` with:
  - `SuccessResponse` (status, message, data)
  - `ErrorResponse` (status, error_code, message, details)
  - `PaginatedResponse` (items, total, page, page_size)

### 3. Create `src/api/models/plugin.py`

- [ ] `PluginInfo` model (id, name, version, enabled, description, display_modes)
- [ ] `PluginConfigResponse` (plugin_id, config as `dict[str, Any]`, schema as `dict[str, Any]`)
- [ ] `PluginToggleRequest` (plugin_id, enabled)
- [ ] `PluginInstallRequest` (plugin_id, source_url)

### 4. Create `src/api/models/system.py`

- [ ] `SystemStatusResponse` (cpu_percent, memory_percent, cpu_temp, disk_percent, service_active, uptime)
- [ ] `SystemVersionResponse` (version, python_version, platform)
- [ ] `HealthResponse` (status, checks dict)

### 5. Tests

- [ ] Write tests for `AppSettings` env var loading
- [ ] Write tests for model serialization/deserialization
- [ ] Verify `PluginConfigResponse.config` remains a plain dict

### 6. Commit

```bash
git add src/api/config.py src/api/models/
git commit -m "feat(api): add Pydantic settings and request/response models"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Models are importable
python3 -c "
from src.api.config import AppSettings, get_settings
from src.api.models.config import SystemConfigResponse, ConfigUpdateRequest
from src.api.models.common import SuccessResponse, ErrorResponse
from src.api.models.plugin import PluginInfo, PluginConfigResponse
from src.api.models.system import SystemStatusResponse, HealthResponse
print('OK: all models importable')
"

# 2. AppSettings reads env vars
LEDMATRIX_PORT=8080 python3 -c "
from src.api.config import AppSettings
s = AppSettings()
assert s.port == 8080, f'Expected 8080, got {s.port}'
print('OK: env var override works')
"

# 3. Plugin config stays as dict
python3 -c "
from src.api.models.plugin import PluginConfigResponse
r = PluginConfigResponse(plugin_id='test', config={'enabled': True}, schema={})
assert isinstance(r.config, dict), 'config must be dict'
print('OK: plugin config is plain dict')
"

# 4. Existing ConfigManager is untouched
python3 -c "
from src.config_manager import ConfigManager
print('OK: ConfigManager still importable')
"

# 5. Run tests
# distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_api_models.py -v --override-ini=\"addopts=\"'
```

---

## Notes

- The `ConfigManager`, `ConfigService`, and `ConfigManagerAtomic` are NOT modified. They coexist per architecture guardrail until Phase 7.
- Pydantic models are for FastAPI route validation only. Plugins continue to receive plain dicts.
- The `SecretStoreModel` is a thin wrapper -- it reads `config_secrets.json` and provides typed access. A full `SecretStore` abstraction (file-backed + env-backed) is deferred to Phase 7.
- `model_config = ConfigDict(from_attributes=True)` allows creating models from ORM objects or dataclasses in the future.
