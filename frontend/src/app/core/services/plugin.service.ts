import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';
import type {
  PluginInfo,
  PluginConfigResponse,
  StorePlugin,
} from '../models/plugin.model';

@Injectable({ providedIn: 'root' })
export class PluginService {
  private readonly api = inject(ApiService);

  list(): Observable<SuccessResponse<PluginInfo[]>> {
    return this.api.get('/plugins/installed');
  }

  get(
    pluginId: string,
  ): Observable<SuccessResponse<PluginConfigResponse>> {
    return this.api.get(
      `/plugins/config?plugin_id=${encodeURIComponent(pluginId)}`,
    );
  }

  getConfig(
    pluginId: string,
  ): Observable<SuccessResponse<PluginConfigResponse>> {
    return this.api.get(
      `/plugins/config?plugin_id=${encodeURIComponent(pluginId)}`,
    );
  }

  updateConfig(
    pluginId: string,
    config: Record<string, unknown>,
  ): Observable<SuccessResponse> {
    return this.api.post('/plugins/config', {
      plugin_id: pluginId,
      config,
    });
  }

  toggle(pluginId: string, enabled: boolean): Observable<SuccessResponse> {
    return this.api.post('/plugins/toggle', {
      plugin_id: pluginId,
      enabled,
    });
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
