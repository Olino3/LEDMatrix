import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';
import type {
  SystemConfigResponse,
  ConfigUpdateRequest,
  ScheduleConfig,
} from '../models/config.model';

@Injectable({ providedIn: 'root' })
export class ConfigService {
  private readonly api = inject(ApiService);

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
