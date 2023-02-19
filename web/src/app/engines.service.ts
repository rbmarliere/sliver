import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Engine } from './engine';

@Injectable({
  providedIn: 'root'
})
export class EnginesService {
  url = 'v1/engines';

  constructor(private http: HttpClient) { }

  getEngines(): Observable<Engine[]> {
    return this.http.get<Engine[]>(this.url);
  }

  createEngine(engine: Engine): Observable<Engine> {
    return this.http.post<Engine>(this.url, engine);
  }
}
