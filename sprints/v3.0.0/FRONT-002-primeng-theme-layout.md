# FRONT-002 — PrimeNG Integration and Dark Theme Layout

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v3.0.0 — Frontend Modernization
**Type:** Feat
**Depends on:** [FRONT-001](FRONT-001-angular-project-scaffold.md)
**Blocks:** [FRONT-004](FRONT-004-dashboard-module.md), [FRONT-005](FRONT-005-plugins-module.md), [FRONT-006](FRONT-006-settings-module.md)

---

## Context

The ROADMAP specifies a dark-first theme using PrimeNG's theming API, with a responsive layout usable on phone/tablet. This ticket installs PrimeNG, configures the dark theme, and builds the application shell layout (sidebar navigation, top bar, content area) that all feature modules will render into.

The current HTMX UI uses Tailwind CSS with a light theme. The new Angular UI switches to PrimeNG components for consistency and accessibility, with a dark-first design appropriate for an LED matrix controller (often viewed in low-light environments).

---

## Acceptance Criteria

- [ ] PrimeNG and PrimeIcons are installed and configured in the Angular project
- [ ] A dark theme is active by default (Aura Dark or Lara Dark)
- [ ] Application shell contains: collapsible sidebar, top bar with system status, main content area
- [ ] Sidebar navigation has entries for: Dashboard, Plugins, Settings, Logs, Store
- [ ] Layout is responsive -- sidebar collapses to hamburger menu on mobile
- [ ] Loading, error, and empty state components exist as reusable shared components
- [ ] `ng build` still produces a valid production bundle

---

## Implementation Checklist

### 1. Install PrimeNG dependencies

- [ ] `npm install primeng primeicons @primeng/themes`
- [ ] Import PrimeNG styles in `angular.json` styles array or `styles.scss`
- [ ] Configure dark theme preset in `app.config.ts` using `providePrimeNG({ theme: { preset: Aura } })`

### 2. Create application shell layout

- [ ] Create `src/app/layout/` directory for shell components
- [ ] Create `AppLayoutComponent` with sidebar + topbar + router-outlet structure
- [ ] Use PrimeNG `Sidebar` or `Drawer` for navigation panel
- [ ] Use PrimeNG `Toolbar` for top bar
- [ ] Add router-outlet in the main content area

### 3. Build sidebar navigation

- [ ] Create `SidebarComponent` with PrimeNG `Menu` or `PanelMenu`
- [ ] Navigation items: Dashboard (`/`), Plugins (`/plugins`), Settings (`/settings`), Logs (`/logs`), Store (`/store`)
- [ ] Use PrimeIcons for each nav item
- [ ] Highlight active route using `routerLinkActive`

### 4. Make layout responsive

- [ ] Sidebar visible by default on desktop (>= 768px)
- [ ] Sidebar hidden behind hamburger toggle on mobile (< 768px)
- [ ] Content area fills remaining width
- [ ] Test at 375px, 768px, and 1024px breakpoints

### 5. Create shared state components

- [ ] `LoadingComponent` -- spinner overlay with optional message
- [ ] `ErrorStateComponent` -- error icon, message, retry button
- [ ] `EmptyStateComponent` -- icon, message, optional action button
- [ ] Export all from a `SharedModule` or shared barrel export

### 6. Commit

```bash
git add frontend/
git commit -m "feat(frontend): integrate PrimeNG with dark theme and app shell layout"
```

---

## Verification Steps

Run these commands after implementation; every one must pass before closing this ticket.

```bash
# 1. PrimeNG is in dependencies
cd frontend && grep -q "primeng" package.json && echo "OK: primeng installed"

# 2. Build succeeds with PrimeNG
cd frontend && npx ng build && echo "OK: build with PrimeNG"

# 3. Layout component exists
test -f frontend/src/app/layout/app-layout.component.ts && echo "OK: layout component"

# 4. Shared components exist
test -f frontend/src/app/shared/loading/loading.component.ts && echo "OK: loading component"
test -f frontend/src/app/shared/error-state/error-state.component.ts && echo "OK: error-state component"
test -f frontend/src/app/shared/empty-state/empty-state.component.ts && echo "OK: empty-state component"

# 5. Navigation routes defined
grep -q "Dashboard" frontend/src/app/layout/sidebar/sidebar.component.ts && echo "OK: nav items defined"
```

---

## Notes

- PrimeNG 17+ uses standalone component imports -- no `PrimeNGModule` needed. Import individual components like `ButtonModule`, `MenuModule`, etc.
- The Aura Dark theme is the recommended default. If Aura is not available in the installed version, use Lara Dark.
- Do NOT build any feature module content in this ticket. The Dashboard, Plugins, Settings, Logs, and Store modules are separate tickets.
- PrimeNG theming is configured via `providePrimeNG()` in `app.config.ts`, not via CSS imports (PrimeNG v17+ style).
- PrimeFlex (utility CSS) is optional. Use it if helpful for layout, but do not duplicate Tailwind patterns.
