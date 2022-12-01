import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import { Credential } from './credential';

@Injectable({
  providedIn: 'root'
})
export class CredentialService {

  url = 'v1/credentials';

  constructor(private http: HttpClient) { }

  getCredentials(): Observable<Credential[]> {
    return this.http
      .get<Credential[]>(this.url)
      .pipe(
        shareReplay()
      );
  }

  addCredential(cred: Credential): Observable<Credential> {
    return this.http.post<Credential>(this.url, cred);
  }

  deleteCredential(exchange_id: number): Observable<any> {
    const opt = {
      headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
      body: { exchange_id: exchange_id }
    };
    return this.http.delete(this.url, opt);
  }
}
