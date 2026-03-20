import { HttpErrorResponse } from '@angular/common/http';
import { ApiError } from './api-error';

describe('ApiError', () => {
  it('should parse a structured error response', () => {
    const httpError = new HttpErrorResponse({
      error: {
        status: 'error',
        error_code: 'NOT_FOUND',
        message: 'Plugin not found',
        details: { plugin_id: 'foo' },
      },
      status: 404,
      statusText: 'Not Found',
    });

    const apiError = ApiError.fromHttpError(httpError);

    expect(apiError.errorCode).toBe('NOT_FOUND');
    expect(apiError.message).toBe('Plugin not found');
    expect(apiError.statusCode).toBe(404);
    expect(apiError.details).toEqual({ plugin_id: 'foo' });
  });

  it('should handle unstructured error responses', () => {
    const httpError = new HttpErrorResponse({
      error: 'Internal Server Error',
      status: 500,
      statusText: 'Internal Server Error',
    });

    const apiError = ApiError.fromHttpError(httpError);

    expect(apiError.errorCode).toBe('UNKNOWN');
    expect(apiError.statusCode).toBe(500);
    expect(apiError.message).toBe('Internal Server Error');
  });

  it('should handle network errors (status 0)', () => {
    const httpError = new HttpErrorResponse({
      error: new ProgressEvent('error'),
      status: 0,
      statusText: 'Unknown Error',
    });

    const apiError = ApiError.fromHttpError(httpError);

    expect(apiError.errorCode).toBe('NETWORK_ERROR');
    expect(apiError.statusCode).toBe(0);
    expect(apiError.message).toBe('Network error — server may be unreachable');
  });
});
