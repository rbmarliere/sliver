import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { ActivatedRoute } from '@angular/router';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
import { Order } from '../order';
import { OrderService } from '../order.service';

@Component({
  selector: 'app-order',
  templateUrl: './order.component.html',
  styleUrls: ['./order.component.less']
})
export class OrderComponent implements OnInit {

  orders: Order[] = [];
  displayedColumns: string[] = [
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

  loading: Boolean = true;

  constructor(
    private orderService: OrderService,
    private dialog: MatDialog,
    private route: ActivatedRoute,
  ) { }

  ngOnInit(): void {
    const position_id = Number(this.route.snapshot.paramMap.get('position_id'));
    this.getOrders(position_id);
  }

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  getOrders(position_id: number): void {
    this.orderService.getOrders(position_id).subscribe({
      next: (res) => {
        this.orders = res;
        this.loading = false;
      },
      error: (err) => this.handleError(err)
    });
  }
}
