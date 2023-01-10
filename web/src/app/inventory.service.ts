import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Inventory } from './inventory';

@Injectable({
  providedIn: 'root'
})
export class InventoryService {

  url = 'v1/inventory';

  constructor(private http: HttpClient) { }

  getInventory(): Observable<Inventory> {
    return this.http
      .get<Inventory>(this.url);
  }
}
