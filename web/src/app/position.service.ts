import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { Position } from './position';

@Injectable({
  providedIn: 'root'
})
export class PositionService {

  url = 'v1/positions';

  constructor(private http: HttpClient) { }

  getPositions(): Observable<Position[]> {
    return this.http
      .get<Position[]>(this.url)
      .pipe(
        shareReplay()
      );
  }
}
