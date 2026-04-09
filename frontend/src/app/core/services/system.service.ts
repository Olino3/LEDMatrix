import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import type { SuccessResponse } from '../models/common.model';
import type {
  SystemStatus,
  SystemVersion,
  HealthResponse,
} from '../models/system.model';

@Injectable({ providedIn: 'root' })
export class SystemService {
  private readonly api = inject(ApiService);

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
