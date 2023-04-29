import { HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { Observable } from 'rxjs';
import { DialogComponent } from './dialog/dialog.component';

@Injectable({
  providedIn: 'root'
})
export class DialogService {

  constructor(private dialog: MatDialog) { }

  handleError(error: HttpErrorResponse) {
    let message: string;
    console.log(error);
    message = error.error.message;
    if (typeof message === 'object') {
      message = JSON.stringify(message);
    }
    if (message === undefined) {
      // message = error.error.error.message;
      message = error.statusText;
    }

    let title: string = "Error";

    switch (error.status) {
      case 403:
        message = 'Access Denied.';
        break;

      case 500:
        title = 'Internal Server Error.';
        break;

      case 504:
        message = 'API is not responding.';
        break;

      default:
        break;
    }

    const dialogConfig = new MatDialogConfig;
    dialogConfig.data = {
      error: true,
      title: title,
      msg: message
    };

    this.dialog.open(DialogComponent, dialogConfig);
  }

  confirm(message: string): Observable<boolean> {
    const dialogConfig = new MatDialogConfig;
    dialogConfig.data = {
      confirm: true,
      msg: message
    };

    const dialogRef = this.dialog.open(DialogComponent, dialogConfig);

    return dialogRef.afterClosed();
  }
}
