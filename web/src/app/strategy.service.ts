import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root',
})
export class StrategyService {
  url = 'v1/strategy';

  constructor(private http: HttpClient) { }

  getStrategy(strategy_id: number): Observable<Strategy> {
    return this.http.get<Strategy>(`${this.url}/${strategy_id}`);
  }

  updateSubscription(strategy: Strategy): Observable<Strategy> {
    return this.http.get<Strategy>(`${this.url}/${strategy.id}?subscribe=${!strategy.subscribed}`);
  }

  updateStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http.put<Strategy>(`${this.url}/${strategy.id}`, strategy);
  }

  deleteStrategy(strategy_id: number): Observable<any> {
    return this.http.delete<any>(`${this.url}/${strategy_id}`);
  }

  updateActive(strategy: Strategy): Observable<Strategy> {
    return this.http.get<Strategy>(`${this.url}/${strategy.id}?active=${!strategy.active}`);
  }
}
