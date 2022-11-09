import * as moment from 'moment';

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

import { BehaviorSubject } from 'rxjs';

import { User } from './user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  authenticated = new BehaviorSubject<boolean>(false);

  private getExpiration() {
    const expiration = localStorage.getItem('expires_at');
    if (expiration === null) {
      return null;
    }
    const expiresAt = JSON.parse(expiration);
    return moment(expiresAt);
  }

  constructor(
    private http: HttpClient,
    private router: Router
  ) { }

  login(email: string, password: string) {
    return this.http.post<User>('/v1/login', { email, password });
  }

  logout() {
    localStorage.removeItem('access_key');
    localStorage.removeItem('expires_at');
    this.authenticated.next(false);
    this.router.navigateByUrl('/login');
    location.reload();
  }

  setSession(authResult: User) {
    const expiresAt = moment(authResult.expires_at, 'X');
    localStorage.setItem('access_key', authResult.access_key);
    localStorage.setItem('expires_at', JSON.stringify(expiresAt.valueOf()));
    this.authenticated.next(true)
    this.router.navigate(['positions']);
  }

  isAuthenticated() {
    if (moment().isBefore(this.getExpiration())) {
      this.authenticated.next(true);
    } else {
      this.authenticated.next(false);
    }
    return this.authenticated.asObservable();
  }

}
