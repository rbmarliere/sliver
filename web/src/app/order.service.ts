import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { Order } from './order';

@Injectable({
  providedIn: 'root'
})
export class OrderService {

  url = 'v1/orders';

  constructor(private http: HttpClient) { }

  transformDate(orders: Order[]): Order[] {
    for (let order of orders) {
      order.time = order.time.slice(0, 16);
    }

    return orders;
  }

  getOrders(position_id: number): Observable<Order[]> {
    return this.http
      .get<Order[]>(this.url + "/" + position_id)
      .pipe(
        map(this.transformDate)
      );
  }
}
