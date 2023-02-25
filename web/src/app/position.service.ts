import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { Position } from './position';

@Injectable({
  providedIn: 'root'
})
export class PositionService {

  url = 'v1/positions';

  constructor(
    private http: HttpClient,
  ) { }

  transformDates(positions: Position[]): Position[] {
    for (let position of positions) {
      position.entry_time = new Date(position.entry_time);
      position.exit_time = new Date(position.exit_time);
    }

    return positions;
  }

  transformDate(position: Position): Position {
    position.entry_time = new Date(position.entry_time);
    position.exit_time = new Date(position.exit_time);
    return position;
  }

  getPositions(): Observable<Position[]> {
    return this.http.get<Position[]>(this.url)
      .pipe(
        map(this.transformDates)
      );
  }

  getPositionsByStrategyId(strategyId: number): Observable<Position[]> {
    return this.http.get<Position[]>(`${this.url}/strategy/${strategyId}`)
      .pipe(
        map(this.transformDates)
      );
  }

  getPosition(positionId: number): Observable<Position> {
    return this.http.get<Position>(`v1/position/${positionId}`)
      .pipe(
        map(this.transformDate)
      );
  }
}
