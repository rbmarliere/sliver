import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { ErrorDialogComponent } from './error-dialog/error-dialog.component';

@Injectable({
  providedIn: 'root'
})
export class DialogService {

  constructor(private dialog: MatDialog) { }

  handleError(error: HttpErrorResponse) {
    let message: string;

    switch (error.status) {
      case 403:
        message = 'Access Denied.';
        break;

      case 500:
        message = 'Internal Server Error.';
        break;

      case 504:
        message = 'API is not responding.';
        break;

      default:
        message = error.error.message;

        if (message === undefined) {
          message = error.error.error.message;
        }

        if (typeof message === 'object') {
          message = JSON.stringify(message);
        }
        break;

    }

    const dialogConfig = new MatDialogConfig;
    dialogConfig.data = {
      msg: message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

}
