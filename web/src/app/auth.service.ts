import * as moment from 'moment';

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { User } from './user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private getExpiration() {
    const expiration = localStorage.getItem('expires_at')
    if (expiration === null) {
      return null
    }
    const expiresAt = JSON.parse(expiration);
    return moment(expiresAt)
  }

  constructor(private http: HttpClient) { }

  login(email: string, password: string) {
    return this.http.post<User>('/v1/login', { email, password });
  }

  logout() {
    localStorage.removeItem('access_key')
    localStorage.removeItem('expires_at')
  }

  isAuthenticated() {
    return moment().isBefore(this.getExpiration())
  }

}
