# FRONT-003: API Service Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a typed Angular service layer with TypeScript interfaces matching the FastAPI backend, an SSE client with auto-reconnect, and domain services for system, plugin, and config operations.

**Architecture:** All services use Angular's `providedIn: 'root'` for tree-shakeable singletons. A base `ApiService` wraps `HttpClient` with typed generics and UUID request headers. An `SseService` wraps native `EventSource` in RxJS Observables with exponential backoff reconnect. Domain services (`SystemService`, `PluginService`, `ConfigService`) delegate to `ApiService`. A functional HTTP interceptor converts error responses to typed `ApiError` instances.

**Tech Stack:** Angular 21 (standalone), TypeScript 5.9, RxJS 7.8, Vitest (via `@angular/build:unit-test`)

---

## File Structure

```
frontend/src/app/core/
├── models/
│   ├── system.model.ts        — SystemStatus, SystemVersion, HealthResponse interfaces
│   ├── plugin.model.ts        — PluginInfo, PluginConfig, PluginToggleRequest, StorePlugin interfaces
│   ├── config.model.ts        — SystemConfig, ScheduleConfig, ConfigUpdateRequest interfaces
│   ├── common.model.ts        — SuccessResponse, ErrorResponse, PaginatedResponse interfaces
│   └── stream.model.ts        — StatsEvent, DisplayEvent, LogEvent interfaces
├── services/
│   ├── api.service.ts         — Base HTTP wrapper with typed generics
│   ├── api.service.spec.ts    — Tests for ApiService
│   ├── sse.service.ts         — EventSource → Observable wrapper with reconnect
│   ├── sse.service.spec.ts    — Tests for SseService
│   ├── system.service.ts      — System domain service
│   ├── system.service.spec.ts — Tests for SystemService
│   ├── plugin.service.ts      — Plugin domain service
│   ├── plugin.service.spec.ts — Tests for PluginService
│   ├── config.service.ts      — Config domain service
│   └── config.service.spec.ts — Tests for ConfigService
├── interceptors/
│   └── error.interceptor.ts   — Functional HTTP error interceptor
├── errors/
│   ├── api-error.ts           — ApiError class
│   └── api-error.spec.ts      — Tests for ApiError
└── index.ts                   — Public API barrel export
```

**Modified files:**
- `frontend/src/app/app.config.ts` — Add `provideHttpClient(withInterceptors([...]))` and `provideAnimationsAsync()`

---

## Scope & Out-of-Scope

**In scope (this ticket):** Models for all API types, ApiService, SseService, SystemService, PluginService, ConfigService, error interceptor, ApiError class.

**Out of scope (future tickets):**
- `FontService` — SPIKE: FRONT-003a
- `WifiService` — SPIKE: FRONT-003b
- `StarlarkService` — SPIKE: FRONT-003c
- `AssetService` — covered by FRONT-005 (plugins module)

These domain services follow the same pattern established here and can be added as needed by downstream tickets.

---

## Task 1: TypeScript Model Interfaces

**Files:**
- Create: `frontend/src/app/core/models/common.model.ts`
- Create: `frontend/src/app/core/models/system.model.ts`
- Create: `frontend/src/app/core/models/plugin.model.ts`
- Create: `frontend/src/app/core/models/config.model.ts`
- Create: `frontend/src/app/core/models/stream.model.ts`

These are pure type definitions (interfaces) — no runtime logic, no TDD needed.

- [ ] **Step 1: Create common.model.ts**

```typescript
// Matches src/api/models/common.py
export interface SuccessResponse<T = unknown> {
  status: string;
  message: string;
  data: T | null;
}

export interface ErrorResponse {
  status: string;
  error_code: string;
  message: string;
  details: Record<string, unknown> | null;
}

export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

- [ ] **Step 2: Create system.model.ts**

```typescript
// Matches src/api/models/system.py
export interface SystemStatus {
  cpu_percent: number;
  memory_percent: number;
  cpu_temp: number | null;
  disk_percent: number;
  service_active: boolean;
  uptime: number;
}

export interface SystemVersion {
  version: string;
  python_version: string;
  platform: string;
}

export interface HealthResponse {
  status: string;
  checks: Record<string, unknown>;
}
```

- [ ] **Step 3: Create plugin.model.ts**

```typescript
// Matches src/api/models/plugin.py
export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  enabled: boolean;
  description: string;
  display_modes: string[];
}

export interface PluginConfigResponse {
  plugin_id: string;
  config: Record<string, unknown>;
  schema: Record<string, unknown>;
}

export interface PluginToggleRequest {
  plugin_id: string;
  enabled: boolean;
}

export interface PluginInstallRequest {
  plugin_id: string;
  source_url: string;
}

// Store plugin — based on store router response shape
export interface StorePlugin {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  tags: string[];
  installed: boolean;
}
```

- [ ] **Step 4: Create config.model.ts**

```typescript
// Matches src/api/models/config.py
export interface DisplayHardwareConfig {
  rows: number;
  cols: number;
  chain_length: number;
  parallel: number;
  brightness: number;
  hardware_mapping: string;
  scan_mode: number;
  pwm_bits: number;
  pwm_dither_bits: number;
  pwm_lsb_nanoseconds: number;
  disable_hardware_pulsing: boolean;
  inverse_colors: boolean;
  show_refresh_rate: boolean;
  led_rgb_sequence: string;
  limit_refresh_rate_hz: number;
}

export interface ScheduleConfig {
  enabled: boolean;
  mode: string;
  start_time: string;
  end_time: string;
}

export interface SystemConfigResponse {
  display: Record<string, unknown>;
  schedule: Record<string, unknown>;
  general: Record<string, unknown>;
}

export interface ConfigUpdateRequest {
  display?: Record<string, unknown>;
  schedule?: Record<string, unknown>;
  general?: Record<string, unknown>;
}
```

- [ ] **Step 5: Create stream.model.ts**

```typescript
// Matches SSE event shapes from src/api/routers/streams.py
export interface StatsEvent {
  timestamp: number;
  uptime: string;
  service_active: boolean;
  cpu_percent: number;
  memory_used_percent: number;
  cpu_temp: number;
  disk_used_percent: number;
}

export interface DisplayEvent {
  timestamp: number;
  width: number;
  height: number;
  image: string | null; // base64-encoded PNG
}

export interface LogEvent {
  timestamp: number;
  logs: string;
}
```

- [ ] **Step 6: Commit models**

```bash
git add frontend/src/app/core/models/
git commit -m "feat(frontend): add TypeScript interfaces for API response types"
```

---

## Task 2: ApiError Class

**Files:**
- Create: `frontend/src/app/core/errors/api-error.ts`
- Create: `frontend/src/app/core/errors/api-error.spec.ts`

- [ ] **Step 1: Write failing test**

```typescript
// api-error.spec.ts
import { HttpErrorResponse } from '@angular/common/http';
import { ApiError } from './api-error';

describe('ApiError', () => {
  it('should parse a structured error response', () => {
    const httpError = new HttpErrorResponse({
      error: {
        status: 'error',
        error_code: 'NOT_FOUND',
        message: 'Plugin not found',
        details: { plugin_id: 'foo' },
      },
      status: 404,
      statusText: 'Not Found',
    });

    const apiError = ApiError.fromHttpError(httpError);

    expect(apiError.errorCode).toBe('NOT_FOUND');
    expect(apiError.message).toBe('Plugin not found');
    expect(apiError.statusCode).toBe(404);
    expect(apiError.details).toEqual({ plugin_id: 'foo' });
  });

  it('should handle unstructured error responses', () => {
    const httpError = new HttpErrorResponse({
      error: 'Internal Server Error',
      status: 500,
      statusText: 'Internal Server Error',
    });

    const apiError = ApiError.fromHttpError(httpError);

    expect(apiError.errorCode).toBe('UNKNOWN');
    expect(apiError.statusCode).toBe(500);
    expect(apiError.message).toBe('Internal Server Error');
  });

  it('should handle network errors (status 0)', () => {
    const httpError = new HttpErrorResponse({
      error: new ProgressEvent('error'),
      status: 0,
      statusText: 'Unknown Error',
    });

    const apiError = ApiError.fromHttpError(httpError);

    expect(apiError.errorCode).toBe('NETWORK_ERROR');
    expect(apiError.statusCode).toBe(0);
    expect(apiError.message).toBe('Network error — server may be unreachable');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: FAIL — `ApiError` not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// api-error.ts
import { HttpErrorResponse } from '@angular/common/http';
import type { ErrorResponse } from '../models/common.model';

export class ApiError extends Error {
  readonly errorCode: string;
  readonly statusCode: number;
  readonly details: Record<string, unknown> | null;

  constructor(message: string, errorCode: string, statusCode: number, details: Record<string, unknown> | null = null) {
    super(message);
    this.name = 'ApiError';
    this.errorCode = errorCode;
    this.statusCode = statusCode;
    this.details = details;
  }

  static fromHttpError(httpError: HttpErrorResponse): ApiError {
    if (httpError.status === 0) {
      return new ApiError('Network error — server may be unreachable', 'NETWORK_ERROR', 0);
    }

    const body = httpError.error;
    if (body && typeof body === 'object' && 'error_code' in body) {
      const err = body as ErrorResponse;
      return new ApiError(err.message, err.error_code, httpError.status, err.details);
    }

    return new ApiError(
      typeof body === 'string' ? body : httpError.statusText,
      'UNKNOWN',
      httpError.status,
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/errors/
git commit -m "feat(frontend): add ApiError class with HTTP error parsing"
```

---

## Task 3: HTTP Error Interceptor

**Files:**
- Create: `frontend/src/app/core/interceptors/error.interceptor.ts`
- Modify: `frontend/src/app/app.config.ts`

The interceptor is a functional interceptor (Angular 21 style) — no class needed.

- [ ] **Step 1: Write the interceptor**

```typescript
// error.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ApiError } from '../errors/api-error';
import { environment } from '../../../environments/environment';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (!environment.production) {
        console.error(`[API Error] ${req.method} ${req.url}:`, error);
      }
      return throwError(() => ApiError.fromHttpError(error));
    }),
  );
};
```

- [ ] **Step 2: Wire up app.config.ts**

Add `provideHttpClient(withInterceptors([errorInterceptor]))`:

```typescript
// app.config.ts
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { errorInterceptor } from './core/interceptors/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([errorInterceptor])),
  ]
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/core/interceptors/ frontend/src/app/app.config.ts
git commit -m "feat(frontend): add HTTP error interceptor with ApiError conversion"
```

---

## Task 4: Base ApiService

**Files:**
- Create: `frontend/src/app/core/services/api.service.ts`
- Create: `frontend/src/app/core/services/api.service.spec.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// api.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';

describe('ApiService', () => {
  let service: ApiService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ApiService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should send GET request with correct base URL', () => {
    service.get<SuccessResponse>('/system/status').subscribe();
    const req = httpTesting.expectOne('/api/v3/system/status');
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: null });
  });

  it('should include X-Request-ID header', () => {
    service.get('/system/version').subscribe();
    const req = httpTesting.expectOne('/api/v3/system/version');
    const requestId = req.request.headers.get('X-Request-ID');
    expect(requestId).toBeTruthy();
    expect(requestId!.length).toBeGreaterThan(0);
    req.flush({ status: 'success', message: 'ok', data: null });
  });

  it('should send POST request with body', () => {
    const body = { plugin_id: 'clock', enabled: true };
    service.post('/plugins/toggle', body).subscribe();
    const req = httpTesting.expectOne('/api/v3/plugins/toggle');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(body);
    req.flush({ status: 'success', message: 'toggled', data: null });
  });

  it('should send PUT request', () => {
    const body = { display: { brightness: 50 } };
    service.put('/config/main', body).subscribe();
    const req = httpTesting.expectOne('/api/v3/config/main');
    expect(req.request.method).toBe('PUT');
    req.flush({ status: 'success', message: 'updated', data: null });
  });

  it('should send DELETE request', () => {
    service.delete('/fonts/custom-font').subscribe();
    const req = httpTesting.expectOne('/api/v3/fonts/custom-font');
    expect(req.request.method).toBe('DELETE');
    req.flush({ status: 'success', message: 'deleted', data: null });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -30`
Expected: FAIL — `ApiService` not found

- [ ] **Step 3: Implement ApiService**

```typescript
// api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = environment.apiBase;

  constructor(private readonly http: HttpClient) {}

  get<T>(path: string): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}${path}`, { headers: this.headers() });
  }

  post<T>(path: string, body: unknown = {}): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${path}`, body, { headers: this.headers() });
  }

  put<T>(path: string, body: unknown = {}): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}${path}`, body, { headers: this.headers() });
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(`${this.baseUrl}${path}`, { headers: this.headers() });
  }

  private headers(): HttpHeaders {
    return new HttpHeaders({ 'X-Request-ID': crypto.randomUUID() });
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -30`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/services/api.service.ts frontend/src/app/core/services/api.service.spec.ts
git commit -m "feat(frontend): add base ApiService with typed HTTP methods"
```

---

## Task 5: SSE Service

**Files:**
- Create: `frontend/src/app/core/services/sse.service.ts`
- Create: `frontend/src/app/core/services/sse.service.spec.ts`

The SSE service wraps native `EventSource` in RxJS Observables with auto-reconnect.

- [ ] **Step 1: Write failing tests**

```typescript
// sse.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { SseService } from './sse.service';
import type { StatsEvent } from '../models/stream.model';

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onopen: (() => void) | null = null;
  readyState = 0;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
    // Simulate connection open
    setTimeout(() => {
      this.readyState = 1;
      this.onopen?.();
    });
  }

  close = vi.fn();

  simulateMessage(data: string): void {
    this.onmessage?.({ data } as MessageEvent);
  }

  simulateError(): void {
    this.readyState = 2;
    this.onerror?.(new Event('error'));
  }
}

describe('SseService', () => {
  let service: SseService;

  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal('EventSource', MockEventSource);
    TestBed.configureTestingModule({});
    service = TestBed.inject(SseService);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should create EventSource and emit parsed messages', () => {
    const values: StatsEvent[] = [];
    const sub = service.connect<StatsEvent>('/stream/stats').subscribe(v => values.push(v));

    const instance = MockEventSource.instances[0];
    expect(instance.url).toBe('/api/v3/stream/stats');

    instance.simulateMessage(JSON.stringify({ timestamp: 1, cpu_percent: 50, memory_used_percent: 40, cpu_temp: 55, disk_used_percent: 30, uptime: 'Running', service_active: true }));
    expect(values).toHaveLength(1);
    expect(values[0].cpu_percent).toBe(50);

    sub.unsubscribe();
    expect(instance.close).toHaveBeenCalled();
  });

  it('should close EventSource on unsubscribe', () => {
    const sub = service.connect('/stream/logs').subscribe();
    const instance = MockEventSource.instances[0];
    sub.unsubscribe();
    expect(instance.close).toHaveBeenCalled();
  });

  it('should provide typed stream accessors', () => {
    expect(service.statsStream$).toBeDefined();
    expect(service.displayStream$).toBeDefined();
    expect(service.logStream$).toBeDefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -30`
Expected: FAIL — `SseService` not found

- [ ] **Step 3: Implement SseService**

```typescript
// sse.service.ts
import { Injectable, NgZone } from '@angular/core';
import { Observable, share, Subject } from 'rxjs';
import { environment } from '../../../environments/environment';
import type { StatsEvent, DisplayEvent, LogEvent } from '../models/stream.model';

@Injectable({ providedIn: 'root' })
export class SseService {
  private readonly baseUrl = environment.apiBase;

  constructor(private readonly zone: NgZone) {}

  connect<T>(endpoint: string): Observable<T> {
    return new Observable<T>(subscriber => {
      const url = `${this.baseUrl}${endpoint}`;
      let eventSource: EventSource;
      let retryCount = 0;
      let retryTimeout: ReturnType<typeof setTimeout> | null = null;

      const createConnection = (): void => {
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
          retryCount = 0;
        };

        eventSource.onmessage = (event: MessageEvent) => {
          this.zone.run(() => {
            try {
              subscriber.next(JSON.parse(event.data) as T);
            } catch {
              // Skip unparseable messages
            }
          });
        };

        eventSource.onerror = () => {
          eventSource.close();
          // Exponential backoff: 1s, 2s, 4s, 8s, ... max 30s
          const delay = Math.min(1000 * Math.pow(2, retryCount), 30_000);
          retryCount++;
          retryTimeout = setTimeout(() => createConnection(), delay);
        };
      };

      createConnection();

      return () => {
        if (retryTimeout !== null) {
          clearTimeout(retryTimeout);
        }
        eventSource?.close();
      };
    });
  }

  readonly statsStream$: Observable<StatsEvent> = this.connect<StatsEvent>('/stream/stats').pipe(share());
  readonly displayStream$: Observable<DisplayEvent> = this.connect<DisplayEvent>('/stream/display').pipe(share());
  readonly logStream$: Observable<LogEvent> = this.connect<LogEvent>('/stream/logs').pipe(share());
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -30`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/services/sse.service.ts frontend/src/app/core/services/sse.service.spec.ts
git commit -m "feat(frontend): add SSE service with auto-reconnect and typed streams"
```

---

## Task 6: SystemService

**Files:**
- Create: `frontend/src/app/core/services/system.service.ts`
- Create: `frontend/src/app/core/services/system.service.spec.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// system.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SystemService } from './system.service';

describe('SystemService', () => {
  let service: SystemService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SystemService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  it('should get system status', () => {
    service.getStatus().subscribe(res => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne(r => r.url.endsWith('/system/status'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { cpu_percent: 10 } });
  });

  it('should get system version', () => {
    service.getVersion().subscribe(res => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne(r => r.url.endsWith('/system/version'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { version: '3.0.0' } });
  });

  it('should get health', () => {
    service.getHealth().subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/health'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'healthy', checks: {} });
  });

  it('should perform system action', () => {
    service.performAction('restart').subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/system/action'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ action: 'restart' });
    req.flush({ status: 'success', message: 'restarting', data: null });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 3: Implement SystemService**

```typescript
// system.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';
import type { SystemStatus, SystemVersion, HealthResponse } from '../models/system.model';

@Injectable({ providedIn: 'root' })
export class SystemService {
  constructor(private readonly api: ApiService) {}

  getStatus(): Observable<SuccessResponse<SystemStatus>> {
    return this.api.get('/system/status');
  }

  getVersion(): Observable<SuccessResponse<SystemVersion>> {
    return this.api.get('/system/version');
  }

  getHealth(): Observable<HealthResponse> {
    return this.api.get('/health');
  }

  performAction(action: string): Observable<SuccessResponse> {
    return this.api.post('/system/action', { action });
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/services/system.service.ts frontend/src/app/core/services/system.service.spec.ts
git commit -m "feat(frontend): add SystemService for system status, health, version"
```

---

## Task 7: PluginService

**Files:**
- Create: `frontend/src/app/core/services/plugin.service.ts`
- Create: `frontend/src/app/core/services/plugin.service.spec.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// plugin.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PluginService } from './plugin.service';

describe('PluginService', () => {
  let service: PluginService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(PluginService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  it('should list plugins', () => {
    service.list().subscribe(res => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne(r => r.url.endsWith('/plugins/installed'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: [] });
  });

  it('should get single plugin by id', () => {
    service.get('clock').subscribe();
    const req = httpTesting.expectOne(r => r.url.includes('/plugins/config') && r.url.includes('plugin_id=clock'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { plugin_id: 'clock', config: {}, schema: {} } });
  });

  it('should get plugin config', () => {
    service.getConfig('clock').subscribe();
    const req = httpTesting.expectOne(r => r.url.includes('/plugins/config') && r.url.includes('plugin_id=clock'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { plugin_id: 'clock', config: {}, schema: {} } });
  });

  it('should update plugin config', () => {
    const config = { brightness: 50 };
    service.updateConfig('clock', config).subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/plugins/config'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ plugin_id: 'clock', config });
    req.flush({ status: 'success', message: 'saved', data: null });
  });

  it('should toggle plugin', () => {
    service.toggle('clock', true).subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/plugins/toggle'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ plugin_id: 'clock', enabled: true });
    req.flush({ status: 'success', message: 'toggled', data: null });
  });

  it('should install plugin', () => {
    service.install('weather').subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/plugins/install'));
    expect(req.request.method).toBe('POST');
    req.flush({ status: 'success', message: 'installed', data: null });
  });

  it('should uninstall plugin', () => {
    service.uninstall('weather').subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/plugins/uninstall'));
    expect(req.request.method).toBe('POST');
    req.flush({ status: 'success', message: 'uninstalled', data: null });
  });

  it('should get store plugins', () => {
    service.getStorePlugins().subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/plugins/store/list'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: [] });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 3: Implement PluginService**

```typescript
// plugin.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';
import type { PluginInfo, PluginConfigResponse, StorePlugin } from '../models/plugin.model';

@Injectable({ providedIn: 'root' })
export class PluginService {
  constructor(private readonly api: ApiService) {}

  list(): Observable<SuccessResponse<PluginInfo[]>> {
    return this.api.get('/plugins/installed');
  }

  get(pluginId: string): Observable<SuccessResponse<PluginConfigResponse>> {
    return this.api.get(`/plugins/config?plugin_id=${encodeURIComponent(pluginId)}`);
  }

  getConfig(pluginId: string): Observable<SuccessResponse<PluginConfigResponse>> {
    return this.api.get(`/plugins/config?plugin_id=${encodeURIComponent(pluginId)}`);
  }

  updateConfig(pluginId: string, config: Record<string, unknown>): Observable<SuccessResponse> {
    return this.api.post('/plugins/config', { plugin_id: pluginId, config });
  }

  toggle(pluginId: string, enabled: boolean): Observable<SuccessResponse> {
    return this.api.post('/plugins/toggle', { plugin_id: pluginId, enabled });
  }

  install(pluginId: string): Observable<SuccessResponse> {
    return this.api.post('/plugins/install', { plugin_id: pluginId });
  }

  uninstall(pluginId: string): Observable<SuccessResponse> {
    return this.api.post('/plugins/uninstall', { plugin_id: pluginId });
  }

  getStorePlugins(): Observable<SuccessResponse<StorePlugin[]>> {
    return this.api.get('/plugins/store/list');
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/services/plugin.service.ts frontend/src/app/core/services/plugin.service.spec.ts
git commit -m "feat(frontend): add PluginService for plugin CRUD and store operations"
```

---

## Task 8: ConfigService

**Files:**
- Create: `frontend/src/app/core/services/config.service.ts`
- Create: `frontend/src/app/core/services/config.service.spec.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// config.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ConfigService } from './config.service';

describe('ConfigService', () => {
  let service: ConfigService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ConfigService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpTesting.verify());

  it('should get main config', () => {
    service.getMainConfig().subscribe(res => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne(r => r.url.endsWith('/config/main'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { display: {}, schedule: {}, general: {} } });
  });

  it('should update main config', () => {
    const update = { display: { brightness: 80 } };
    service.updateMainConfig(update).subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/config/main'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(update);
    req.flush({ status: 'success', message: 'saved', data: null });
  });

  it('should get schedule', () => {
    service.getSchedule().subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/config/schedule'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { enabled: false, mode: 'global', start_time: '07:00', end_time: '23:00' } });
  });

  it('should update schedule', () => {
    const schedule = { enabled: true, mode: 'global', start_time: '08:00', end_time: '22:00' };
    service.updateSchedule(schedule).subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/config/schedule'));
    expect(req.request.method).toBe('POST');
    req.flush({ status: 'success', message: 'saved', data: null });
  });

  it('should get secrets', () => {
    service.getSecrets().subscribe();
    const req = httpTesting.expectOne(r => r.url.endsWith('/config/secrets'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: {} });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: FAIL

- [ ] **Step 3: Implement ConfigService**

```typescript
// config.service.ts
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';
import type { SystemConfigResponse, ConfigUpdateRequest, ScheduleConfig } from '../models/config.model';

@Injectable({ providedIn: 'root' })
export class ConfigService {
  constructor(private readonly api: ApiService) {}

  getMainConfig(): Observable<SuccessResponse<SystemConfigResponse>> {
    return this.api.get('/config/main');
  }

  updateMainConfig(config: ConfigUpdateRequest): Observable<SuccessResponse> {
    return this.api.post('/config/main', config);
  }

  getSchedule(): Observable<SuccessResponse<ScheduleConfig>> {
    return this.api.get('/config/schedule');
  }

  updateSchedule(schedule: Partial<ScheduleConfig>): Observable<SuccessResponse> {
    return this.api.post('/config/schedule', schedule);
  }

  getSecrets(): Observable<SuccessResponse<Record<string, unknown>>> {
    return this.api.get('/config/secrets');
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/core/services/config.service.ts frontend/src/app/core/services/config.service.spec.ts
git commit -m "feat(frontend): add ConfigService for config and schedule operations"
```

---

## Task 9: Barrel Export and Build Verification

**Files:**
- Create: `frontend/src/app/core/index.ts`

- [ ] **Step 1: Create barrel export**

```typescript
// index.ts — public API for core module
// Models
export * from './models/common.model';
export * from './models/system.model';
export * from './models/plugin.model';
export * from './models/config.model';
export * from './models/stream.model';

// Errors
export { ApiError } from './errors/api-error';

// Services
export { ApiService } from './services/api.service';
export { SseService } from './services/sse.service';
export { SystemService } from './services/system.service';
export { PluginService } from './services/plugin.service';
export { ConfigService } from './services/config.service';
```

- [ ] **Step 2: Run full test suite**

Run: `cd frontend && npx ng test -- --run --reporter=verbose 2>&1 | tail -40`
Expected: All tests pass

- [ ] **Step 3: Run production build**

Run: `cd frontend && npx ng build 2>&1 | tail -10`
Expected: Build succeeds with no errors

- [ ] **Step 4: Run lint**

Run: `cd frontend && npx ng lint 2>&1 | tail -10`
Expected: No lint errors (fix any that arise)

- [ ] **Step 5: Run verification checks from ticket**

```bash
test -f frontend/src/app/core/services/api.service.ts && echo "OK: api service"
test -f frontend/src/app/core/services/sse.service.ts && echo "OK: sse service"
test -f frontend/src/app/core/services/system.service.ts && echo "OK: system service"
test -f frontend/src/app/core/services/plugin.service.ts && echo "OK: plugin service"
test -f frontend/src/app/core/services/config.service.ts && echo "OK: config service"
test -f frontend/src/app/core/models/system.model.ts && echo "OK: system models"
test -f frontend/src/app/core/models/plugin.model.ts && echo "OK: plugin models"
test -f frontend/src/app/core/models/common.model.ts && echo "OK: common models"
test -f frontend/src/app/core/models/stream.model.ts && echo "OK: stream models"
grep -q "error.interceptor\|errorInterceptor" frontend/src/app/app.config.ts && echo "OK: interceptor registered"
```

- [ ] **Step 6: Commit barrel and finalize**

```bash
git add frontend/src/app/core/index.ts
git commit -m "feat(frontend): add barrel export for core service layer"
```

---

## SPIKE Tickets (Out of Scope)

The following domain services are NOT covered by this ticket but will be needed by downstream feature modules. Create these as separate tickets:

### SPIKE: FRONT-003a — FontService
**Scope:** `FontService` wrapping `/api/v3/fonts/*` endpoints (catalog, upload, preview, overrides, delete). Needed by settings module.

### SPIKE: FRONT-003b — WifiService
**Scope:** `WifiService` wrapping `/api/v3/wifi/*` endpoints (status, scan, connect, disconnect, AP mode). Needed by settings module.

### SPIKE: FRONT-003c — StarlarkService
**Scope:** `StarlarkService` wrapping `/api/v3/starlark/*` endpoints (apps CRUD, repository, pixlet install). Needed by plugins module if Starlark support is exposed.

These follow the exact same pattern as SystemService/PluginService/ConfigService — inject `ApiService`, add typed methods. Each should take ~15 minutes to implement.
