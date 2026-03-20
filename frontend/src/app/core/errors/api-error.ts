import { HttpErrorResponse } from '@angular/common/http';
import type { ErrorResponse } from '../models/common.model';

export class ApiError extends Error {
  readonly errorCode: string;
  readonly statusCode: number;
  readonly details: Record<string, unknown> | null;

  constructor(
    message: string,
    errorCode: string,
    statusCode: number,
    details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.errorCode = errorCode;
    this.statusCode = statusCode;
    this.details = details;
  }

  static fromHttpError(httpError: HttpErrorResponse): ApiError {
    if (httpError.status === 0) {
      return new ApiError('Network error — server may be unreachable', 'NETWORK_ERROR', 0);
    }

    const body = httpError.error;
    if (body && typeof body === 'object' && 'error_code' in body) {
      const err = body as ErrorResponse;
      return new ApiError(err.message, err.error_code, httpError.status, err.details);
    }

    return new ApiError(
      typeof body === 'string' ? body : httpError.statusText,
      'UNKNOWN',
      httpError.status,
    );
  }
}
