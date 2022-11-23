import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Order } from './order';

@Injectable({
  providedIn: 'root'
})
export class OrderService {

  url = 'v1/orders';

  constructor(private http: HttpClient) { }

  getOrders(position_id: number): Observable<Order[]> {
    return this.http
      .get<Order[]>(this.url + "/" + position_id);
  }
}
