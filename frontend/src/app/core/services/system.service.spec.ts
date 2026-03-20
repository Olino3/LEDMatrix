import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
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
    service.getStatus().subscribe((res) => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/system/status'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: { cpu_percent: 10 } });
  });

  it('should get system version', () => {
    service.getVersion().subscribe((res) => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/system/version'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      status: 'success',
      message: 'ok',
      data: { version: '3.0.0' },
    });
  });

  it('should get health', () => {
    service.getHealth().subscribe();
    const req = httpTesting.expectOne((r) => r.url.endsWith('/health'));
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'healthy', checks: {} });
  });

  it('should perform system action', () => {
    service.performAction('restart').subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/system/action'),
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ action: 'restart' });
    req.flush({ status: 'success', message: 'restarting', data: null });
  });
});
