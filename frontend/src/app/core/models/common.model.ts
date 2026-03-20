/** Matches src/api/models/common.py */

export interface SuccessResponse<T = unknown> {
  status: string;
  message: string;
  data: T | null;
}

export interface ErrorResponse {
  status: string;
  error_code: string;
  message: string;
  details: Record<string, unknown> | null;
}

export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
