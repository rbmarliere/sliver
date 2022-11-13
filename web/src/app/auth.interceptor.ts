import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private router: Router) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const accessKey = localStorage.getItem('access_key');


    if (accessKey) {

      const authReq = request.clone({
        headers: request.headers.set("Authorization", "Bearer " + accessKey)
      });

      return next.handle(authReq);

    } else {
      return next.handle(request).pipe(tap(
        (err: any) => {
          if (err instanceof HttpErrorResponse) {
            if (err.status === 401) {
              this.router.navigateByUrl('/login');
            }
          }
        }
      ));
    }

  }
}
