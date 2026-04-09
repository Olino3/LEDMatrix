/** Matches src/api/models/config.py */

export interface DisplayHardwareConfig {
  rows: number;
  cols: number;
  chain_length: number;
  parallel: number;
  brightness: number;
  hardware_mapping: string;
  scan_mode: number;
  pwm_bits: number;
  pwm_dither_bits: number;
  pwm_lsb_nanoseconds: number;
  disable_hardware_pulsing: boolean;
  inverse_colors: boolean;
  show_refresh_rate: boolean;
  led_rgb_sequence: string;
  limit_refresh_rate_hz: number;
}

export interface ScheduleConfig {
  enabled: boolean;
  mode: string;
  start_time: string;
  end_time: string;
}

export interface SystemConfigResponse {
  display: Record<string, unknown>;
  schedule: Record<string, unknown>;
  general: Record<string, unknown>;
}

export interface ConfigUpdateRequest {
  display?: Record<string, unknown>;
  schedule?: Record<string, unknown>;
  general?: Record<string, unknown>;
}
