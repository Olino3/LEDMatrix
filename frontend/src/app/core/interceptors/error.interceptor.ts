import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ApiError } from '../errors/api-error';
import { environment } from '../../../environments/environment';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (!environment.production) {
        console.error(`[API Error] ${req.method} ${req.url}:`, error);
      }
      return throwError(() => ApiError.fromHttpError(error));
    }),
  );
};
