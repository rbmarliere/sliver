import {
  HttpErrorResponse,
  HttpEvent, HttpHandler, HttpInterceptor, HttpRequest
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';
import { DialogService } from './dialog.service';

@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {

  constructor(private dialogService: DialogService) { }

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((err: HttpErrorResponse) => {
        this.dialogService.handleError(err);
        return throwError(() => err);
      }));
  }
}

