/** Matches src/api/models/system.py */

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
