import * as moment from 'moment';

import { Component, OnInit } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../auth.service';
import { User } from '../user';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.less']
})
export class LoginComponent implements OnInit {

  form = this.formBuilder.group({ email: '', password: '' });

  private setSession(authResult: User) {
    const expiresAt = moment.unix(authResult.expires_at);

    localStorage.setItem('access_key', authResult.access_key);
    localStorage.setItem('expires_at', JSON.stringify(expiresAt.valueOf()));

    this.router.navigate(['positions']);
  }

  private handleError(error: HttpErrorResponse) {
    window.alert(error.error.message);
  }

  constructor(
    private authService: AuthService,
    private formBuilder: FormBuilder,
    private router: Router
  ) { }

  ngOnInit(): void { }

  login() {
    const val = this.form.value;

    if (val.email && val.password) {
      this.authService
        .login(val.email, val.password)
        .subscribe({
          next: (res) => this.setSession(res),
          error: (err) => this.handleError(err)
        });
    }

  }

}
