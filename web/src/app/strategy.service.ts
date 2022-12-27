import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root',
})
export class StrategyService {
  url = 'v1/strategy';

  constructor(private http: HttpClient) { }

  transformDate(strategies: Strategy[]): Strategy[] {
    for (let strategy of strategies) {
      strategy.next_refresh = strategy.next_refresh.slice(0, 16);
    }

    return strategies;
  }

  getStrategy(strategy_id: number): Observable<Strategy> {
    return this.http.get<Strategy>(this.url + '/' + strategy_id).pipe(
      map((st) => {
        st.next_refresh = st.next_refresh.slice(0, 16);
        return st;
      })
    );
  }

  updateSubscription(strategy: Strategy): Observable<Strategy> {
    const req = { subscribed: !strategy.subscribed };
    return this.http.put<Strategy>(this.url + '/' + strategy.id, req).pipe(
      map((st) => {
        st.next_refresh = st.next_refresh.slice(0, 16);
        return st;
      })
    );
  }

  updateStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http.put<Strategy>(this.url + '/' + strategy.id, strategy).pipe(
      map((st) => {
        st.next_refresh = st.next_refresh.slice(0, 16);
        return st;
      })
    );
  }

  deleteStrategy(strategy_id: number): Observable<any> {
    return this.http.delete<any>(this.url + '/' + strategy_id);
  }
}
