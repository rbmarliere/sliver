import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import { User } from './user';

@Injectable({
  providedIn: 'root'
})
export class UserService {

  url = 'v1/user';

  constructor(private http: HttpClient) { }

  getUser(): Observable<User> {
    return this.http
      .get<User>(this.url)
      .pipe(
        shareReplay()
      );
  }

  updateUser(user: User): Observable<any> {
    return this.http.put(this.url, user);
  }
}
