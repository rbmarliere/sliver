import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root',
})
export class StrategiesService {
  url = 'v1/strategies';

  constructor(private http: HttpClient) { }

  getStrategies(): Observable<Strategy[]> {
    return this.http.get<Strategy[]>(this.url);
  }

  createStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http.post<Strategy>(this.url, strategy);
  }

  getStrategiesByMarketId(market_id: number): Observable<Strategy[]> {
    return this.http.get<Strategy[]>(`${this.url}/market/${market_id}`);
  }
}
