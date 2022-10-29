import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor
} from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor() {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const accessKey = localStorage.getItem('access_key');


    if (accessKey) {

      const authReq = request.clone({
        headers: request.headers.set("Authorization", "Bearer " + accessKey)
      });

      return next.handle(authReq);

    } else {
      return next.handle(request);
    }

  }
}
