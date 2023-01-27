import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseStrategy, Strategy } from './strategy';

@Injectable({
  providedIn: 'root',
})
export class StrategiesService {
  url = 'v1/strategies';

  constructor(private http: HttpClient) { }

  getStrategies(): Observable<BaseStrategy[]> {
    return this.http.get<BaseStrategy[]>(this.url);
  }

  createStrategy(strategy: BaseStrategy): Observable<BaseStrategy> {
    return this.http.post<BaseStrategy>(this.url, strategy);
  }

  getStrategiesByTimeframe(timeframe: string): Observable<Strategy[]> {
    return this.http.get<BaseStrategy[]>(`${this.url}/timeframe/${timeframe}`);
  }

  getStrategiesByMarketId(market_id: number): Observable<Strategy[]> {
    return this.http.get<BaseStrategy[]>(`${this.url}/market/${market_id}`);
  }
}
