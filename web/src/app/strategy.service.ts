import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root'
})
export class StrategyService {

  strategies_url = 'v1/strategies';
  strategy_url = 'v1/strategy';

  constructor(private http: HttpClient) { }

  transformDate(strategies: Strategy[]): Strategy[] {
    for (let strategy of strategies) {
      strategy.next_refresh = strategy.next_refresh.slice(0, 16);
    }

    return strategies;
  }

  getStrategies(): Observable<Strategy[]> {
    return this.http
      .get<Strategy[]>(this.strategies_url)
      .pipe(
        map(this.transformDate)
      );
  }

  getStrategy(strategy_id: number): Observable<Strategy> {
    return this.http
      .get<Strategy>(this.strategy_url + "/" + strategy_id)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }

  updateSubscription(strategy: Strategy): Observable<Strategy> {
    const req = { id: strategy.id, subscribed: !strategy.subscribed };
    return this.http
      .post<Strategy>(this.strategies_url, req)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }

  updateStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http
      .put<Strategy>(this.strategies_url, strategy)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }

  createStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http
      .post<Strategy>(this.strategies_url, strategy)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }
}
