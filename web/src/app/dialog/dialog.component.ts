import { Component, Inject, OnInit } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';

@Component({
  selector: 'app-dialog',
  templateUrl: './dialog.component.html',
  styleUrls: ['./dialog.component.less']
})
export class DialogComponent implements OnInit {

  error: boolean = false;
  confirm: boolean = false;
  title: string;
  msg: string;

  constructor(
    public dialogRef: MatDialogRef<DialogComponent>,
    @Inject(MAT_DIALOG_DATA) data: any
  ) {
    if (data.error) this.error = data.error;
    if (data.confirm) this.confirm = data.confirm;
    this.title = data.title;
    this.msg = data.msg;
  }

  ngOnInit(): void {
  }

}

