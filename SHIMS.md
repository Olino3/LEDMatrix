# Active Compatibility Shims

Shims maintained per migration conventions (`.claude/rules/migration.md`).
Each shim re-exports at the original import path with a `DeprecationWarning`.

| Original path | New path | Consumers | Added | Removal phase |
|---|---|---|---|---|
| `web_interface_v2.increment_api_counter` | `src.api.services.api_counter.increment_api_counter` | `ledmatrix-music`, `ledmatrix-weather`, `odds-ticker`, `youtube-stats` | v2.0.0 | v6.2.0 (Phase 9) |
