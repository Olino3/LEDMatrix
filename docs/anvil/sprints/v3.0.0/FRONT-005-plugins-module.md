# FRONT-005 — Plugins Feature Module

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-002](FRONT-002-primeng-theme-layout.md), [FRONT-003](FRONT-003-api-service-layer.md)
**Blocks:** _(none)_

---

## Context

The Plugins module replaces the HTMX "Plugins" partial (`web_interface/templates/v3/partials/plugins.html` and `plugin_config.html`). It provides a grid/list view of all installed plugins with enable/disable toggles, and a detail view for editing individual plugin configuration against its JSON Schema.

The backend provides:
- `GET /api/v3/plugins` -- list all plugins with status
- `GET /api/v3/plugins/{id}` -- single plugin info
- `GET /api/v3/plugins/{id}/config` -- plugin config + schema
- `PUT /api/v3/plugins/{id}/config` -- update plugin config
- `POST /api/v3/plugins/{id}/toggle` -- enable/disable
- `GET /api/v3/plugins/{id}/health` -- plugin health metrics

---

## Acceptance Criteria

- [ ] Plugins route is lazy-loaded at `/plugins`
- [ ] Plugin list view shows all installed plugins in a responsive grid
- [ ] Each plugin card shows: name, version, enabled status, description
- [ ] Enable/disable toggle sends `POST /api/v3/plugins/{id}/toggle` and updates UI optimistically
- [ ] Plugin detail view at `/plugins/:id` shows full config form
- [ ] Config form is dynamically generated from the plugin's `config_schema.json`
- [ ] Config changes are saved via `PUT /api/v3/plugins/{id}/config`
- [ ] Success/error toast notifications on save

---

## Implementation Checklist

### 1. Create plugins module structure

- [ ] Create `frontend/src/app/features/plugins/` directory
- [ ] Add lazy route in `app.routes.ts`: `{ path: 'plugins', loadComponent: () => import(...) }`
- [ ] Add child route: `{ path: ':id', loadComponent: () => import(...) }` for detail view

### 2. Build plugin list view

- [ ] Create `PluginListComponent` as the route entry point
- [ ] Fetch plugins from `PluginService.list()`
- [ ] Display in PrimeNG `DataView` with grid/list toggle
- [ ] Each card: plugin icon (from `/api/v3/plugins/assets/{id}/icon` or default), name, version, description
- [ ] PrimeNG `ToggleSwitch` for enable/disable with optimistic update
- [ ] Search/filter bar using PrimeNG `InputText` with debounced filtering

### 3. Build plugin detail / config view

- [ ] Create `PluginConfigComponent` for the `:id` route
- [ ] Fetch config and schema from `PluginService.getConfig(id)`
- [ ] Dynamically generate form fields from JSON Schema using a `SchemaFormComponent`
- [ ] Support field types: string (InputText), number (InputNumber), boolean (ToggleSwitch), enum (Dropdown), object (nested fieldset)
- [ ] Show plugin health metrics (last update time, error count) from `/api/v3/plugins/{id}/health`

### 4. Implement schema-driven form generator

- [ ] Create `frontend/src/app/shared/schema-form/schema-form.component.ts`
- [ ] Input: JSON Schema object + current values
- [ ] Output: form value changes as `EventEmitter<Record<string, any>>`
- [ ] Handle `required` fields, `default` values, `description` as help text
- [ ] Validate against schema constraints (min, max, pattern, enum)

### 5. Add save and notification

- [ ] Save button calls `PluginService.updateConfig(id, formValues)`
- [ ] Show PrimeNG `Toast` on success ("Config saved") and error ("Save failed: ...")
- [ ] Disable save button while request is in-flight (loading state)

### 6. Commit

```bash
git add frontend/src/app/features/plugins/ frontend/src/app/shared/schema-form/
git commit -m "feat(frontend): add plugins module with dynamic config forms"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Plugin components exist
test -f frontend/src/app/features/plugins/plugin-list/plugin-list.component.ts && echo "OK: plugin list"
test -f frontend/src/app/features/plugins/plugin-config/plugin-config.component.ts && echo "OK: plugin config"

# 2. Schema form component exists
test -f frontend/src/app/shared/schema-form/schema-form.component.ts && echo "OK: schema form"

# 3. Routes configured
grep -q "plugins" frontend/src/app/app.routes.ts && echo "OK: plugins route"

# 4. Build succeeds
cd frontend && npx ng build && echo "OK: build with plugins module"
```

---

## Notes

- The JSON Schema form generator is the most complex piece of this ticket. Keep it simple for v3.0.0 -- support flat schemas with basic types. Deeply nested schemas or `$ref` support can be deferred.
- Plugin icons may not exist for all plugins. Use a default icon (PrimeIcons `pi-puzzle-piece`) as fallback.
- The HTMX version uses Alpine.js for dynamic form behavior. The Angular version replaces this entirely with reactive forms.
- Optimistic UI updates for toggle: update the UI immediately, then roll back if the API call fails.
- Plugin config includes standard fields (`enabled`, `display_duration`, `transition`) plus plugin-specific fields. The schema form must handle both.
