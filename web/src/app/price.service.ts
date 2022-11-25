import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import { Price } from './price';

@Injectable({
  providedIn: 'root'
})
export class PriceService {

  url = 'v1/prices';

  constructor(private http: HttpClient) { }

  getPrices(strategy_id: number): Observable<Price> {
    return this.http
      .get<Price>(this.url + "/" + strategy_id)
      .pipe(
        shareReplay()
      );
  }
}
