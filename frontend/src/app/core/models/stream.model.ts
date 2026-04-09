/** Matches SSE event shapes from src/api/routers/streams.py */

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
  image: string | null;
}

export interface LogEvent {
  timestamp: number;
  logs: string;
}
