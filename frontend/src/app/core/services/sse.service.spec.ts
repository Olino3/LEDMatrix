import { TestBed } from '@angular/core/testing';
import { SseService } from './sse.service';
import type { StatsEvent } from '../models/stream.model';

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
    const sub = service
      .connect<StatsEvent>('/stream/stats')
      .subscribe((v) => values.push(v));

    const instance = MockEventSource.instances[0];
    expect(instance.url).toBe('/api/v3/stream/stats');

    instance.simulateMessage(
      JSON.stringify({
        timestamp: 1,
        cpu_percent: 50,
        memory_used_percent: 40,
        cpu_temp: 55,
        disk_used_percent: 30,
        uptime: 'Running',
        service_active: true,
      }),
    );
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
