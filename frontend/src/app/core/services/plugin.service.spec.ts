import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
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
    service.list().subscribe((res) => {
      expect(res.data).toBeTruthy();
    });
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/plugins/installed'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: [] });
  });

  it('should get single plugin by id', () => {
    service.get('clock').subscribe();
    const req = httpTesting.expectOne(
      (r) =>
        r.url.includes('/plugins/config') &&
        r.url.includes('plugin_id=clock'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      status: 'success',
      message: 'ok',
      data: { plugin_id: 'clock', config: {}, schema: {} },
    });
  });

  it('should get plugin config', () => {
    service.getConfig('clock').subscribe();
    const req = httpTesting.expectOne(
      (r) =>
        r.url.includes('/plugins/config') &&
        r.url.includes('plugin_id=clock'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      status: 'success',
      message: 'ok',
      data: { plugin_id: 'clock', config: {}, schema: {} },
    });
  });

  it('should update plugin config', () => {
    const config = { brightness: 50 };
    service.updateConfig('clock', config).subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/plugins/config'),
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ plugin_id: 'clock', config });
    req.flush({ status: 'success', message: 'saved', data: null });
  });

  it('should toggle plugin', () => {
    service.toggle('clock', true).subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/plugins/toggle'),
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ plugin_id: 'clock', enabled: true });
    req.flush({ status: 'success', message: 'toggled', data: null });
  });

  it('should install plugin', () => {
    service.install('weather').subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/plugins/install'),
    );
    expect(req.request.method).toBe('POST');
    req.flush({ status: 'success', message: 'installed', data: null });
  });

  it('should uninstall plugin', () => {
    service.uninstall('weather').subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/plugins/uninstall'),
    );
    expect(req.request.method).toBe('POST');
    req.flush({ status: 'success', message: 'uninstalled', data: null });
  });

  it('should get store plugins', () => {
    service.getStorePlugins().subscribe();
    const req = httpTesting.expectOne((r) =>
      r.url.endsWith('/plugins/store/list'),
    );
    expect(req.request.method).toBe('GET');
    req.flush({ status: 'success', message: 'ok', data: [] });
  });
});
