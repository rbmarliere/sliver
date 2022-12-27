import { Component, OnInit } from '@angular/core';
import { FormBuilder } from '@angular/forms';

import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.less']
})
export class LoginComponent implements OnInit {

  form = this.formBuilder.group({ email: '', password: '' });

  constructor(
    private authService: AuthService,
    private formBuilder: FormBuilder,
  ) { }

  ngOnInit(): void { }

  login() {
    const val = this.form.value;

    if (val.email && val.password) {
      this.authService
        .login(val.email, val.password)
        .subscribe({
          next: (res) => this.authService.setSession(res),
        });
    }

  }

}
