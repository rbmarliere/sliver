import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable, shareReplay } from 'rxjs';

import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root'
})
export class StrategyService {

  url = 'v1/strategies';

  constructor(private http: HttpClient) { }

  transformDate(strategies: Strategy[]): Strategy[] {
    for (let strategy of strategies) {
      strategy.next_refresh = strategy.next_refresh.slice(0, 16);
    }

    return strategies;
  }

  getStrategies(): Observable<Strategy[]> {
    return this.http
      .get<Strategy[]>(this.url)
      .pipe(
        map(this.transformDate)
      );
  }

  updateSubscription(strategy: Strategy): Observable<Strategy> {
    const req = { id: strategy.id, subscribed: !strategy.subscribed };
    return this.http
      .post<Strategy>(this.url, req)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }

  updateStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http
      .put<Strategy>(this.url, strategy)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }

  createStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http
      .post<Strategy>(this.url, strategy)
      .pipe(
        map((st) => {
          st.next_refresh = st.next_refresh.slice(0, 16);
          return st;
        })
      );
  }
}
