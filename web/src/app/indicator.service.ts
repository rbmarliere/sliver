import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { Indicator } from './indicator';
import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root'
})
export class IndicatorService {

  url = 'v1/indicators';

  constructor(
    private http: HttpClient
  ) { }

  transformDates(indicators: Indicator): Indicator {
    for (let i = 0; i < indicators.time.length; i++) {
      indicators.time[i] = new Date(indicators.time[i]);
    }

    return indicators;
  }

  getIndicators(strategy: Strategy): Observable<Indicator> {
    return this.http.get<Indicator>(`${this.url}/${strategy.id}`)
      .pipe(
        map(this.transformDates)
      );
  }
}
