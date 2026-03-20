import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
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
    service.getMainConfig().subscribe((res) => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne((r) => r.url.endsWith('/config/main'));
    expect(req.request.method).toBe('GET');
    req.flush({
      status: 'success',
      message: 'ok',
      data: { display: {}, schedule: {}, general: {} },
    });
  });

  it('should update main config', () => {
    const update = { display: { brightness: 80 } };
    service.updateMainConfig(update).subscribe();
    const req = httpTesting.expectOne((r) => r.url.endsWith('/config/main'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(update);
    req.flush({ status: 'success', message: 'saved', data: null });
  });

  it('should get schedule', () => {
    service.getSchedule().subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/config/schedule'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      status: 'success',
      message: 'ok',
      data: {
        enabled: false,
        mode: 'global',
        start_time: '07:00',
        end_time: '23:00',
      },
    });
  });

  it('should update schedule', () => {
    const schedule = {
      enabled: true,
      mode: 'global',
      start_time: '08:00',
      end_time: '22:00',
    };
    service.updateSchedule(schedule).subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/config/schedule'),
    );
    expect(req.request.method).toBe('POST');
    req.flush({ status: 'success', message: 'saved', data: null });
  });

  it('should get secrets', () => {
    service.getSecrets().subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/config/secrets'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: {} });
  });
});
