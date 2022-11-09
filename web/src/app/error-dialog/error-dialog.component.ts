import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';

@Component({
  selector: 'app-error-dialog',
  templateUrl: './error-dialog.component.html',
  styleUrls: ['./error-dialog.component.less']
})
export class ErrorDialogComponent implements OnInit {

  title: string;
  msg: string;

  constructor(
    @Inject(MAT_DIALOG_DATA) data: any
  ) { 
    this.title = data.title;
    this.msg = data.msg;
  }

  ngOnInit(): void {
  }

}

