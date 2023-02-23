import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Order } from '../order';
import { OrderService } from '../order.service';

@Component({
  selector: 'app-order',
  templateUrl: './order.component.html',
  styleUrls: ['./order.component.less']
})
export class OrderComponent implements OnInit {
  order: Order = {} as Order;
  loading: Boolean = true;

  constructor(
    private orderService: OrderService,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    const order_id = Number(this.route.snapshot.paramMap.get('order_id'));
    this.getOrder(order_id);
  }

  getOrder(order_id: number): void {
    this.orderService.getOrder(order_id).subscribe({
      next: (res) => {
        this.order = res;
        this.loading = false;
      }
    });
  }

}
