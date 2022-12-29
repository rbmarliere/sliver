import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { Credential } from '../credential';
import { CredentialService } from '../credential.service';
import { User } from '../user';
import { UserService } from '../user.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.less']
})
export class DashboardComponent implements OnInit {

  form = this.createForm({
    email: '',
    old_password: '',
    password: '',
    access_key: '',
    expires_at: 0,
    telegram: '',
    max_risk: 0,
    cash_reserve: 0,
    target_factor: 0
  });

  credentials: Credential[] = [];

  constructor(
    private userService: UserService,
    private credentialService: CredentialService,
    private formBuilder: FormBuilder
  ) { }

  ngOnInit(): void {
    this.getUser();
    this.getCredentials();
  }

  createForm(model: User): FormGroup {
    return this.formBuilder.group(model);
  }

  getUser(): void {
    this.userService.getUser().subscribe({
      next: (res) => this.form.patchValue(res)
    });
  }

  getCredentials(): void {
    this.credentialService.getCredentials().subscribe({
      next: (res) => this.credentials = res
    });
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }

  updateUser(): void {
    const user = this.form.value;

    this.userService.updateUser(user).subscribe({
      next: () => location.reload()
    });
  }

}
