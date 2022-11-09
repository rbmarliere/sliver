import { Component, OnInit } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';

import { AuthService } from '../auth.service';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.less']
})
export class LoginComponent implements OnInit {

  form = this.formBuilder.group({ email: '', password: '' });

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private authService: AuthService,
    private formBuilder: FormBuilder,
    private dialog: MatDialog
  ) { }

  ngOnInit(): void { }

  login() {
    const val = this.form.value;

    if (val.email && val.password) {
      this.authService
        .login(val.email, val.password)
        .subscribe({
          next: (res) => this.authService.setSession(res),
          error: (err) => this.handleError(err)
        });
    }

  }

}
