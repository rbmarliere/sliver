import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { Indicator } from './indicator';

@Injectable({
  providedIn: 'root'
})
export class IndicatorService {

  url = 'v1/indicators';

  constructor(
    private http: HttpClient
  ) { }

  transformDates(indicators: Indicator): Indicator {
    if (indicators.time) {
      for (let i = 0; i < indicators.time.length; i++) {
        indicators.time[i] = new Date(indicators.time[i]);
      }
    }

    return indicators;
  }

  getIndicators(strategy_id: number, since?: string, until?: string): Observable<Indicator> {
    let route = `${this.url}/${strategy_id}?`;

    if (since) {
      const since_date = new Date(since);
      const since_time = Math.floor(since_date.getTime() / 1000);
      route += `since=${since_time}&`;
    }

    if (until) {
      const until_date = new Date(until);
      const until_time = Math.floor(until_date.getTime() / 1000);
      route += `until=${until_time}&`;
    }

    return this.http.get<Indicator>(route)
      .pipe(
        map(this.transformDates)
      );
  }
}
