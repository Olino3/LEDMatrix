# SPIKE-002 — Raw JSON Config Editor

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-006](FRONT-006-settings-module.md)
**Blocks:** _(none)_

---

## Context

The HTMX frontend had a "Raw JSON" editor (`web_interface/templates/v3/partials/raw_json.html`) that allows power users to directly edit the full `config.json` and `config_secrets.json` files. This is a power-user feature that should be preserved in the Angular SPA.

The backend provides:
- `POST /api/v3/config/raw/main` -- overwrite full config with raw JSON
- `POST /api/v3/config/raw/secrets` -- overwrite full secrets with raw JSON

---

## Acceptance Criteria

- [ ] Raw JSON editor accessible from Settings page (new tab or sub-route)
- [ ] Code editor component with JSON syntax highlighting
- [ ] JSON validation before save (parse check + optional schema validation)
- [ ] Separate editors for main config and secrets config
- [ ] Confirmation dialog before overwriting ("This will replace the entire config")
- [ ] Success/error toast on save

---

## Implementation Checklist

### 1. Add code editor dependency

- [ ] Install a JSON editor library (e.g., `monaco-editor` via `ngx-monaco-editor` or PrimeNG `Editor`)
- [ ] If Monaco is too heavy, use a simple `<textarea>` with JSON validation

### 2. Create raw JSON editor component

- [ ] Create `frontend/src/app/features/settings/raw-json/raw-json-editor.component.ts`
- [ ] Two tabs: "Main Config" and "Secrets Config"
- [ ] Load current config via `GET /api/v3/config/main` and `GET /api/v3/config/secrets`
- [ ] Display as formatted JSON in the editor

### 3. Add validation and save

- [ ] Validate JSON on every change (syntax check)
- [ ] Show validation errors inline
- [ ] Save button with confirmation dialog
- [ ] Call `POST /api/v3/config/raw/main` or `POST /api/v3/config/raw/secrets`

### 4. Commit

```bash
git add frontend/src/app/features/settings/raw-json/
git commit -m "feat(frontend): add raw JSON config editor for power users"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. Component exists
test -f frontend/src/app/features/settings/raw-json/raw-json-editor.component.ts && echo "OK: raw json editor"

# 2. Build succeeds
cd frontend && npx ng build && echo "OK: build with raw json editor"
```

---

## Notes

- Monaco Editor adds ~2MB to the bundle. If bundle size is a concern, use a lightweight alternative or a simple textarea with `JSON.parse()` validation.
- Secrets config should redact sensitive values on display (the backend already returns redacted values).
- This is a power-user feature. It can be hidden behind an "Advanced" toggle or placed in a less prominent location.
