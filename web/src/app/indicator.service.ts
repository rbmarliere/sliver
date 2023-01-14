import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Indicator } from './indicator';
import { Strategy } from './strategy';

@Injectable({
  providedIn: 'root'
})
export class IndicatorService {
  url = 'v1/indicators';

  constructor(private http: HttpClient) { }

  getIndicators(strategy: Strategy): Observable<Indicator> {
    return this.http.get<Indicator>(`${this.url}/${strategy.id}`);
  }
}
