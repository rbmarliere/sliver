import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Engine } from './engine';

@Injectable({
  providedIn: 'root'
})
export class EngineService {
  url = 'v1/engine';

  constructor(private http: HttpClient) { }

  getEngine(engine_id: number): Observable<Engine> {
    return this.http.get<Engine>(`${this.url}/${engine_id}`);
  }

  deleteEngine(engine_id: number): Observable<any> {
    return this.http.delete<any>(`${this.url}/${engine_id}`);
  }

  updateEngine(engine: Engine): Observable<Engine> {
    return this.http.put<Engine>(`${this.url}/${engine.id}`, engine);
  }

}
