import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Position } from './position';

@Injectable({
  providedIn: 'root'
})
export class PositionService {

  url = 'v1/positions';

  constructor(
    private http: HttpClient,
  ) { }

  getPositions(): Observable<Position[]> {
    return this.http.get<Position[]>(this.url);
  }

  getPositionsByStrategyId(strategyId: number): Observable<Position[]> {
    return this.http.get<Position[]>(`${this.url}/strategy/${strategyId}`);
  }

  getPosition(positionId: number): Observable<Position> {
    return this.http.get<Position>(`v1/position/${positionId}`);
  }
}
