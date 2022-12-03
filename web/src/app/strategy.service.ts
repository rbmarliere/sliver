import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root'
})
export class StrategyService {

  url = 'v1/strategies';

  constructor(private http: HttpClient) { }

  getStrategies(): Observable<Strategy[]> {
    return this.http
      .get<Strategy[]>(this.url)
      .pipe(
        shareReplay()
      );
  }

  updateSubscription(strategy: Strategy): Observable<Strategy> {
    const req = { id: strategy.id, subscribed: !strategy.subscribed };
    return this.http.post<Strategy>(this.url, req);
  }

  updateStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http.put<Strategy>(this.url, strategy);
  }

  createStrategy(strategy: Strategy): Observable<Strategy> {
    return this.http.post<Strategy>(this.url, strategy);
  }
}
