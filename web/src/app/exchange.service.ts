import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Exchange } from './exchange';

@Injectable({
  providedIn: 'root'
})
export class ExchangeService {

  url = 'v1/exchanges';

  constructor(private http: HttpClient) { }

  getExchanges(): Observable<Exchange[]> {
    return this.http.get<Exchange[]>(this.url);
  }
}
