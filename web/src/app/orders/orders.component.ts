import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Order } from '../order';
import { OrderService } from '../order.service';

@Component({
  selector: 'app-orders',
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.less']
})
export class OrdersComponent implements OnInit {

  orders: Order[] = [];
  displayedColumns: string[] = this.getDisplayedColumns();

  loading: Boolean = true;

  constructor(
    private orderService: OrderService,
    private route: ActivatedRoute,
  ) { }

  ngOnInit(): void {
    const position_id = Number(this.route.snapshot.paramMap.get('position_id'));
    this.getOrders(position_id);
  }

  getDisplayedColumns(): string[] {
    if (window.innerWidth < 768) {
      // mobile
      return [
        "exchange_order_id",
        // "time",
        "status",
        // "type",
        "side",
        // "price",
        // "amount",
        // "cost",
        // "filled",
        // "fee",
      ];
    } else {
      return [
        "exchange_order_id",
        "time",
        "status",
        "type",
        "side",
        "price",
        "amount",
        "cost",
        "filled",
        "fee",
      ];
    }
  }

  getOrders(position_id: number): void {
    this.orderService.getOrders(position_id).subscribe({
      next: (res) => {
        this.orders = res;
        this.loading = false;
      },
    });
  }
}
