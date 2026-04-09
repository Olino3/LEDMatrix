# FRONT-002: PrimeNG Integration and Dark Theme Layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install PrimeNG, configure a dark-first theme, and build the application shell layout (sidebar + topbar + content area) that all feature modules render into.

**Architecture:** Standalone Angular components using PrimeNG v20 with Aura dark theme. The `AppLayoutComponent` acts as the shell, composing a `SidebarComponent` (PrimeNG Drawer + Menu) and `TopbarComponent` (PrimeNG Toolbar). Responsive behavior toggles sidebar visibility via a signal. Three shared state components (Loading, ErrorState, EmptyState) are simple presentational components with inputs.

**Tech Stack:** Angular 21, PrimeNG 20, @primeuix/themes (Aura), PrimeIcons, Vitest

**Ticket:** `sprints/v3.0.0/FRONT-002-primeng-theme-layout.md`

---

## File Structure

### New files to create

```
frontend/src/app/
├── layout/
│   ├── app-layout.component.ts       # Shell: composes sidebar + topbar + router-outlet
│   ├── app-layout.component.html     # Template for the shell
│   ├── app-layout.component.scss     # Shell styles (grid/flex layout)
│   ├── app-layout.component.spec.ts  # Tests for layout logic
│   ├── sidebar/
│   │   ├── sidebar.component.ts      # Navigation sidebar with PrimeNG Menu
│   │   ├── sidebar.component.html    # Sidebar template
│   │   ├── sidebar.component.scss    # Sidebar styles
│   │   └── sidebar.component.spec.ts # Tests for sidebar nav items
│   └── topbar/
│       ├── topbar.component.ts       # Top bar with hamburger toggle + title
│       ├── topbar.component.html     # Topbar template
│       ├── topbar.component.scss     # Topbar styles
│       └── topbar.component.spec.ts  # Tests for topbar toggle
├── shared/
│   ├── loading/
│   │   ├── loading.component.ts      # Spinner with optional message
│   │   ├── loading.component.html
│   │   ├── loading.component.scss
│   │   └── loading.component.spec.ts
│   ├── error-state/
│   │   ├── error-state.component.ts  # Error icon + message + retry button
│   │   ├── error-state.component.html
│   │   ├── error-state.component.scss
│   │   └── error-state.component.spec.ts
│   └── empty-state/
│       ├── empty-state.component.ts  # Icon + message + optional action
│       ├── empty-state.component.html
│       ├── empty-state.component.scss
│       └── empty-state.component.spec.ts
```

### Files to modify

```
frontend/package.json                  # New dependencies (via npm install)
frontend/src/app/app.config.ts         # Add providePrimeNG + provideAnimationsAsync
frontend/src/app/app.routes.ts         # Add layout route with children
frontend/src/app/app.ts               # Minimal changes (layout is routed)
frontend/src/app/app.html             # Just router-outlet
frontend/src/index.html               # Add app-dark class for dark-first
frontend/src/styles.scss              # Global dark theme overrides + PrimeIcons
```

---

## Task 1: Install PrimeNG Dependencies

**Files:**
- Modify: `frontend/package.json` (via npm install)

- [ ] **Step 1: Install packages**

```bash
cd frontend && npm install primeng @primeuix/themes primeicons @angular/animations
```

- [ ] **Step 2: Verify installation**

```bash
cd frontend && grep -q '"primeng"' package.json && echo "OK: primeng"
cd frontend && grep -q '"@primeuix/themes"' package.json && echo "OK: @primeuix/themes"
cd frontend && grep -q '"primeicons"' package.json && echo "OK: primeicons"
cd frontend && grep -q '"@angular/animations"' package.json && echo "OK: @angular/animations"
```

- [ ] **Step 3: Commit**

```bash
cd frontend && git add package.json package-lock.json
git commit -m "chore(frontend): install PrimeNG, PrimeIcons, and @primeuix/themes"
```

---

## Task 2: Configure Dark Theme and Animations

**Files:**
- Modify: `frontend/src/app/app.config.ts`
- Modify: `frontend/src/index.html`
- Modify: `frontend/src/styles.scss`

- [ ] **Step 1: Configure providePrimeNG in app.config.ts**

```typescript
import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { providePrimeNG } from 'primeng/config';
import Aura from '@primeuix/themes/aura';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideAnimationsAsync(),
    provideRouter(routes),
    providePrimeNG({
      theme: {
        preset: Aura,
        options: {
          darkModeSelector: '.app-dark',
        },
      },
    }),
  ],
};
```

- [ ] **Step 2: Add dark mode class to index.html**

Add `class="app-dark"` to the `<html>` tag in `frontend/src/index.html` so dark theme is active by default.

- [ ] **Step 3: Add PrimeIcons font import and base styles to styles.scss**

```scss
@import 'primeicons/primeicons.css';

html,
body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: var(--font-family);
  background: var(--p-surface-ground);
  color: var(--p-text-color);
}
```

- [ ] **Step 4: Verify build still works**

```bash
cd frontend && npx ng build
```
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/app.config.ts frontend/src/index.html frontend/src/styles.scss
git commit -m "feat(frontend): configure PrimeNG Aura dark theme"
```

---

## Task 3: Create TopbarComponent

**Files:**
- Create: `frontend/src/app/layout/topbar/topbar.component.ts`
- Create: `frontend/src/app/layout/topbar/topbar.component.html`
- Create: `frontend/src/app/layout/topbar/topbar.component.scss`
- Test: `frontend/src/app/layout/topbar/topbar.component.spec.ts`

- [ ] **Step 1: Write failing test (RED)**

```typescript
// frontend/src/app/layout/topbar/topbar.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TopbarComponent } from './topbar.component';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

describe('TopbarComponent', () => {
  let component: TopbarComponent;
  let fixture: ComponentFixture<TopbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TopbarComponent],
      providers: [provideAnimationsAsync()],
    }).compileComponents();

    fixture = TestBed.createComponent(TopbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit toggleSidebar when hamburger is clicked', () => {
    const spy = vi.fn();
    component.toggleSidebar.subscribe(spy);
    component.onToggleSidebar();
    expect(spy).toHaveBeenCalled();
  });

  it('should display the app title', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('LEDMatrix');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx ng test --watch=false
```
Expected: FAIL — TopbarComponent does not exist.

- [ ] **Step 3: Implement TopbarComponent (GREEN)**

```typescript
// frontend/src/app/layout/topbar/topbar.component.ts
import { Component, output } from '@angular/core';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [ToolbarModule, ButtonModule],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent {
  toggleSidebar = output<void>();

  onToggleSidebar(): void {
    this.toggleSidebar.emit();
  }
}
```

```html
<!-- frontend/src/app/layout/topbar/topbar.component.html -->
<p-toolbar>
  <ng-template #start>
    <p-button
      icon="pi pi-bars"
      [text]="true"
      (click)="onToggleSidebar()"
      aria-label="Toggle sidebar"
    />
    <span class="app-title">LEDMatrix</span>
  </ng-template>
  <ng-template #end>
    <span class="status-indicator">
      <i class="pi pi-circle-fill status-dot"></i>
    </span>
  </ng-template>
</p-toolbar>
```

```scss
// frontend/src/app/layout/topbar/topbar.component.scss
.app-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-left: 0.5rem;
}

.status-dot {
  color: var(--p-green-400);
  font-size: 0.75rem;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx ng test --watch=false
```
Expected: All TopbarComponent tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/layout/topbar/
git commit -m "feat(frontend): add TopbarComponent with hamburger toggle"
```

---

## Task 4: Create SidebarComponent

**Files:**
- Create: `frontend/src/app/layout/sidebar/sidebar.component.ts`
- Create: `frontend/src/app/layout/sidebar/sidebar.component.html`
- Create: `frontend/src/app/layout/sidebar/sidebar.component.scss`
- Test: `frontend/src/app/layout/sidebar/sidebar.component.spec.ts`

- [ ] **Step 1: Write failing test (RED)**

```typescript
// frontend/src/app/layout/sidebar/sidebar.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { SidebarComponent } from './sidebar.component';

describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent],
      providers: [provideRouter([]), provideAnimationsAsync()],
    }).compileComponents();

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have 5 navigation items', () => {
    expect(component.navItems.length).toBe(5);
  });

  it('should have Dashboard as first item with route /', () => {
    expect(component.navItems[0].label).toBe('Dashboard');
    expect(component.navItems[0].routerLink).toBe('/');
  });

  it('should have Plugins item with route /plugins', () => {
    const item = component.navItems.find((i) => i.label === 'Plugins');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/plugins');
  });

  it('should have Settings item with route /settings', () => {
    const item = component.navItems.find((i) => i.label === 'Settings');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/settings');
  });

  it('should have Logs item with route /logs', () => {
    const item = component.navItems.find((i) => i.label === 'Logs');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/logs');
  });

  it('should have Store item with route /store', () => {
    const item = component.navItems.find((i) => i.label === 'Store');
    expect(item).toBeTruthy();
    expect(item!.routerLink).toBe('/store');
  });

  it('should have an icon for each nav item', () => {
    for (const item of component.navItems) {
      expect(item.icon).toBeTruthy();
      expect(item.icon).toMatch(/^pi pi-/);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx ng test --watch=false
```
Expected: FAIL — SidebarComponent does not exist.

- [ ] **Step 3: Implement SidebarComponent (GREEN)**

```typescript
// frontend/src/app/layout/sidebar/sidebar.component.ts
import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';

export interface NavItem {
  label: string;
  icon: string;
  routerLink: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  readonly navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'pi pi-home', routerLink: '/' },
    { label: 'Plugins', icon: 'pi pi-th-large', routerLink: '/plugins' },
    { label: 'Settings', icon: 'pi pi-cog', routerLink: '/settings' },
    { label: 'Logs', icon: 'pi pi-list', routerLink: '/logs' },
    { label: 'Store', icon: 'pi pi-shopping-bag', routerLink: '/store' },
  ];
}
```

```html
<!-- frontend/src/app/layout/sidebar/sidebar.component.html -->
<nav class="sidebar-nav" aria-label="Main navigation">
  @for (item of navItems; track item.routerLink) {
    <a
      [routerLink]="item.routerLink"
      routerLinkActive="active"
      [routerLinkActiveOptions]="item.routerLink === '/' ? { exact: true } : { exact: false }"
      class="nav-item"
    >
      <i [class]="item.icon"></i>
      <span class="nav-label">{{ item.label }}</span>
    </a>
  }
</nav>
```

```scss
// frontend/src/app/layout/sidebar/sidebar.component.scss
.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.5rem;
  color: var(--p-text-color);
  text-decoration: none;
  border-radius: 6px;
  margin: 0.125rem 0.5rem;
  transition: background-color 0.2s;

  &:hover {
    background: var(--p-surface-hover);
  }

  &.active {
    background: var(--p-primary-color);
    color: var(--p-primary-contrast-color);
  }

  i {
    font-size: 1.25rem;
    width: 1.5rem;
    text-align: center;
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx ng test --watch=false
```
Expected: All SidebarComponent tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/layout/sidebar/
git commit -m "feat(frontend): add SidebarComponent with navigation items"
```

---

## Task 5: Create AppLayoutComponent (Shell)

**Files:**
- Create: `frontend/src/app/layout/app-layout.component.ts`
- Create: `frontend/src/app/layout/app-layout.component.html`
- Create: `frontend/src/app/layout/app-layout.component.scss`
- Test: `frontend/src/app/layout/app-layout.component.spec.ts`

- [ ] **Step 1: Write failing test (RED)**

```typescript
// frontend/src/app/layout/app-layout.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { AppLayoutComponent } from './app-layout.component';

describe('AppLayoutComponent', () => {
  let component: AppLayoutComponent;
  let fixture: ComponentFixture<AppLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppLayoutComponent],
      providers: [provideRouter([]), provideAnimationsAsync()],
    }).compileComponents();

    fixture = TestBed.createComponent(AppLayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have sidebarVisible default to true', () => {
    expect(component.sidebarVisible()).toBe(true);
  });

  it('should toggle sidebarVisible when toggleSidebar is called', () => {
    expect(component.sidebarVisible()).toBe(true);
    component.toggleSidebar();
    expect(component.sidebarVisible()).toBe(false);
    component.toggleSidebar();
    expect(component.sidebarVisible()).toBe(true);
  });

  it('should render the topbar', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('app-topbar')).toBeTruthy();
  });

  it('should render a router-outlet for content', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('router-outlet')).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx ng test --watch=false
```
Expected: FAIL — AppLayoutComponent does not exist.

- [ ] **Step 3: Implement AppLayoutComponent (GREEN)**

```typescript
// frontend/src/app/layout/app-layout.component.ts
import { Component, signal, HostListener } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { DrawerModule } from 'primeng/drawer';
import { TopbarComponent } from './topbar/topbar.component';
import { SidebarComponent } from './sidebar/sidebar.component';

const MOBILE_BREAKPOINT = 768;

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [RouterOutlet, DrawerModule, TopbarComponent, SidebarComponent],
  templateUrl: './app-layout.component.html',
  styleUrl: './app-layout.component.scss',
})
export class AppLayoutComponent {
  sidebarVisible = signal(true);
  isMobile = signal(false);

  constructor() {
    this.checkMobile();
  }

  toggleSidebar(): void {
    this.sidebarVisible.update((v) => !v);
  }

  @HostListener('window:resize')
  onResize(): void {
    this.checkMobile();
  }

  private checkMobile(): void {
    if (typeof window !== 'undefined') {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT;
      this.isMobile.set(mobile);
      if (mobile) {
        this.sidebarVisible.set(false);
      }
    }
  }
}
```

```html
<!-- frontend/src/app/layout/app-layout.component.html -->
<div class="app-layout">
  <app-topbar (toggleSidebar)="toggleSidebar()" />

  @if (isMobile()) {
    <!-- Mobile: PrimeNG Drawer overlay -->
    <p-drawer
      [(visible)]="sidebarVisible"
      [modal]="true"
      [showCloseIcon]="true"
      position="left"
      styleClass="app-sidebar-drawer"
    >
      <ng-template #header>
        <span class="drawer-title">LEDMatrix</span>
      </ng-template>
      <app-sidebar />
    </p-drawer>
  } @else {
    <!-- Desktop: static sidebar -->
    @if (sidebarVisible()) {
      <aside class="app-sidebar">
        <app-sidebar />
      </aside>
    }
  }

  <main class="app-content" [class.sidebar-open]="!isMobile() && sidebarVisible()">
    <router-outlet />
  </main>
</div>
```

```scss
// frontend/src/app/layout/app-layout.component.scss
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  padding-top: 60px; // below topbar
  background: var(--p-surface-card);
  border-right: 1px solid var(--p-surface-border);
  overflow-y: auto;
  z-index: 100;
}

.app-content {
  flex: 1;
  padding: 1.5rem;
  margin-top: 60px; // below topbar
  transition: margin-left 0.2s;

  &.sidebar-open {
    margin-left: 240px;
  }
}

.drawer-title {
  font-size: 1.25rem;
  font-weight: 600;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx ng test --watch=false
```
Expected: All AppLayoutComponent tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/layout/app-layout.component.*
git commit -m "feat(frontend): add AppLayoutComponent shell with responsive sidebar"
```

---

## Task 6: Wire Layout into Routing

**Files:**
- Modify: `frontend/src/app/app.routes.ts`
- Modify: `frontend/src/app/app.ts`
- Modify: `frontend/src/app/app.html`

- [ ] **Step 1: Configure routes with layout shell**

```typescript
// frontend/src/app/app.routes.ts
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./layout/app-layout.component').then((m) => m.AppLayoutComponent),
    children: [
      // Feature modules will be lazy-loaded here in FRONT-004/005/006
    ],
  },
];
```

- [ ] **Step 2: Simplify app.html to just router-outlet**

```html
<!-- frontend/src/app/app.html -->
<router-outlet />
```

- [ ] **Step 3: Update app.ts (remove unused title signal)**

```typescript
// frontend/src/app/app.ts
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {}
```

- [ ] **Step 4: Update app.spec.ts to match simplified App component**

The existing `app.spec.ts` tests for a `title` signal and `<h1>` rendering that no longer exist. Replace with tests that match the shell wrapper role.

```typescript
// frontend/src/app/app.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('App', () => {
  let fixture: ComponentFixture<App>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(App);
    fixture.detectChanges();
  });

  it('should create the app', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render a router-outlet', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('router-outlet')).toBeTruthy();
  });
});
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npx ng build
```
Expected: Build succeeds.

- [ ] **Step 6: Run tests**

```bash
cd frontend && npx ng test --watch=false
```
Expected: All tests pass (including updated app.spec.ts).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/app.routes.ts frontend/src/app/app.ts frontend/src/app/app.html frontend/src/app/app.spec.ts
git commit -m "feat(frontend): wire layout shell into app routing"
```

---

## Task 7: Create Shared State Components

**Files:**
- Create: `frontend/src/app/shared/loading/loading.component.ts` + html + scss + spec
- Create: `frontend/src/app/shared/error-state/error-state.component.ts` + html + scss + spec
- Create: `frontend/src/app/shared/empty-state/empty-state.component.ts` + html + scss + spec

### 7a: LoadingComponent

- [ ] **Step 1: Write failing test (RED)**

```typescript
// frontend/src/app/shared/loading/loading.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoadingComponent } from './loading.component';

describe('LoadingComponent', () => {
  let fixture: ComponentFixture<LoadingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoadingComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(LoadingComponent);
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should show default message when none provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.loading-message')?.textContent?.trim()).toBe('Loading...');
  });

  it('should show custom message when provided', () => {
    fixture.componentRef.setInput('message', 'Fetching plugins');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.loading-message')?.textContent?.trim()).toBe('Fetching plugins');
  });

  it('should render a spinner element', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.pi-spin')).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx ng test --watch=false
```

- [ ] **Step 3: Implement LoadingComponent (GREEN)**

```typescript
// frontend/src/app/shared/loading/loading.component.ts
import { Component, input } from '@angular/core';

@Component({
  selector: 'app-loading',
  standalone: true,
  templateUrl: './loading.component.html',
  styleUrl: './loading.component.scss',
})
export class LoadingComponent {
  message = input('Loading...');
}
```

```html
<!-- frontend/src/app/shared/loading/loading.component.html -->
<div class="loading-container">
  <i class="pi pi-spin pi-spinner loading-spinner"></i>
  <span class="loading-message">{{ message() }}</span>
</div>
```

```scss
// frontend/src/app/shared/loading/loading.component.scss
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
}

.loading-spinner {
  font-size: 2.5rem;
  color: var(--p-primary-color);
}

.loading-message {
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx ng test --watch=false
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/shared/loading/
git commit -m "feat(frontend): add LoadingComponent with spinner and message"
```

### 7b: ErrorStateComponent

- [ ] **Step 6: Write failing test (RED)**

```typescript
// frontend/src/app/shared/error-state/error-state.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { ErrorStateComponent } from './error-state.component';

describe('ErrorStateComponent', () => {
  let fixture: ComponentFixture<ErrorStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ErrorStateComponent],
      providers: [provideAnimationsAsync()],
    }).compileComponents();
    fixture = TestBed.createComponent(ErrorStateComponent);
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should display the error message', () => {
    fixture.componentRef.setInput('message', 'Something went wrong');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Something went wrong');
  });

  it('should show default message when none provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('An error occurred');
  });

  it('should emit retry when retry button is clicked', () => {
    fixture.detectChanges();
    const spy = vi.fn();
    fixture.componentInstance.retry.subscribe(spy);
    fixture.componentInstance.onRetry();
    expect(spy).toHaveBeenCalled();
  });

  it('should render an error icon', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.pi-exclamation-circle')).toBeTruthy();
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

```bash
cd frontend && npx ng test --watch=false
```

- [ ] **Step 8: Implement ErrorStateComponent (GREEN)**

```typescript
// frontend/src/app/shared/error-state/error-state.component.ts
import { Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-error-state',
  standalone: true,
  imports: [ButtonModule],
  templateUrl: './error-state.component.html',
  styleUrl: './error-state.component.scss',
})
export class ErrorStateComponent {
  message = input('An error occurred');
  retry = output<void>();

  onRetry(): void {
    this.retry.emit();
  }
}
```

```html
<!-- frontend/src/app/shared/error-state/error-state.component.html -->
<div class="error-container">
  <i class="pi pi-exclamation-circle error-icon"></i>
  <p class="error-message">{{ message() }}</p>
  <p-button label="Retry" icon="pi pi-refresh" (click)="onRetry()" severity="secondary" />
</div>
```

```scss
// frontend/src/app/shared/error-state/error-state.component.scss
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
}

.error-icon {
  font-size: 3rem;
  color: var(--p-red-400);
}

.error-message {
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
  margin: 0;
}
```

- [ ] **Step 9: Run tests to verify they pass**

```bash
cd frontend && npx ng test --watch=false
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/app/shared/error-state/
git commit -m "feat(frontend): add ErrorStateComponent with retry button"
```

### 7c: EmptyStateComponent

- [ ] **Step 11: Write failing test (RED)**

```typescript
// frontend/src/app/shared/empty-state/empty-state.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { EmptyStateComponent } from './empty-state.component';

describe('EmptyStateComponent', () => {
  let fixture: ComponentFixture<EmptyStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmptyStateComponent],
      providers: [provideAnimationsAsync()],
    }).compileComponents();
    fixture = TestBed.createComponent(EmptyStateComponent);
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should display the message', () => {
    fixture.componentRef.setInput('message', 'No plugins found');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('No plugins found');
  });

  it('should show default message when none provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Nothing here yet');
  });

  it('should show action button when actionLabel is provided', () => {
    fixture.componentRef.setInput('actionLabel', 'Add Plugin');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Add Plugin');
  });

  it('should not show action button when actionLabel is not provided', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('p-button')).toBeFalsy();
  });

  it('should emit action when action button is clicked', () => {
    fixture.componentRef.setInput('actionLabel', 'Add Plugin');
    fixture.detectChanges();
    const spy = vi.fn();
    fixture.componentInstance.action.subscribe(spy);
    fixture.componentInstance.onAction();
    expect(spy).toHaveBeenCalled();
  });

  it('should render an icon', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.pi-inbox')).toBeTruthy();
  });
});
```

- [ ] **Step 12: Run test to verify it fails**

```bash
cd frontend && npx ng test --watch=false
```

- [ ] **Step 13: Implement EmptyStateComponent (GREEN)**

```typescript
// frontend/src/app/shared/empty-state/empty-state.component.ts
import { Component, input, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [ButtonModule],
  templateUrl: './empty-state.component.html',
  styleUrl: './empty-state.component.scss',
})
export class EmptyStateComponent {
  icon = input('pi pi-inbox');
  message = input('Nothing here yet');
  actionLabel = input<string | undefined>(undefined);
  action = output<void>();

  onAction(): void {
    this.action.emit();
  }
}
```

```html
<!-- frontend/src/app/shared/empty-state/empty-state.component.html -->
<div class="empty-container">
  <i [class]="icon() + ' empty-icon'"></i>
  <p class="empty-message">{{ message() }}</p>
  @if (actionLabel()) {
    <p-button [label]="actionLabel()!" (click)="onAction()" severity="secondary" />
  }
</div>
```

```scss
// frontend/src/app/shared/empty-state/empty-state.component.scss
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
}

.empty-icon {
  font-size: 3rem;
  color: var(--p-text-muted-color);
}

.empty-message {
  color: var(--p-text-muted-color);
  font-size: 0.95rem;
  margin: 0;
}
```

- [ ] **Step 14: Run tests to verify they pass**

```bash
cd frontend && npx ng test --watch=false
```

- [ ] **Step 15: Commit**

```bash
git add frontend/src/app/shared/empty-state/
git commit -m "feat(frontend): add EmptyStateComponent with optional action button"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
cd frontend && npx ng test --watch=false
```
Expected: All tests pass.

- [ ] **Step 2: Run lint**

```bash
cd frontend && npx ng lint
```
Expected: No lint errors.

- [ ] **Step 3: Run production build**

```bash
cd frontend && npx ng build
```
Expected: Build succeeds, output in `frontend/dist/ledmatrix/browser/`.

- [ ] **Step 4: Run ticket verification commands**

```bash
cd frontend && grep -q "primeng" package.json && echo "OK: primeng installed"
cd frontend && npx ng build && echo "OK: build with PrimeNG"
test -f frontend/src/app/layout/app-layout.component.ts && echo "OK: layout component"
test -f frontend/src/app/shared/loading/loading.component.ts && echo "OK: loading component"
test -f frontend/src/app/shared/error-state/error-state.component.ts && echo "OK: error-state component"
test -f frontend/src/app/shared/empty-state/empty-state.component.ts && echo "OK: empty-state component"
grep -q "Dashboard" frontend/src/app/layout/sidebar/sidebar.component.ts && echo "OK: nav items defined"
```

- [ ] **Step 5: Update ticket status**

Edit `sprints/v3.0.0/FRONT-002-primeng-theme-layout.md` — change `**Status:** Open` to `**Status:** Done`.

---

## Notes

- **PrimeNG v20** uses `@primeuix/themes` (not `@primeng/themes` as the ticket suggests — package was renamed). The import is `import Aura from '@primeuix/themes/aura'`.
- **Dark-first:** Achieved by adding `class="app-dark"` to `<html>` in `index.html` and setting `darkModeSelector: '.app-dark'` in PrimeNG config. This can later be toggled to support light mode.
- **`@angular/animations`** must be installed as a dependency for `provideAnimationsAsync()` which PrimeNG requires.
- **No feature module content** is built in this ticket — Dashboard, Plugins, Settings, Logs, Store are separate tickets (FRONT-004/005/006).
- **Responsive approach:** Desktop shows a static sidebar. Mobile (< 768px) uses PrimeNG Drawer as an overlay triggered by hamburger button.
- The sidebar uses plain `<a routerLink>` rather than PrimeNG Menu to keep it simple and fully styled with the dark theme. PrimeNG Menu could be swapped in later if needed.
