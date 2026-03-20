import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
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
