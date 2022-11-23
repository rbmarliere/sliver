import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { Credential } from '../credential';
import { CredentialService } from '../credential.service';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';
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

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig;

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  constructor(
    private userService: UserService,
    private credentialService: CredentialService,
    private dialog: MatDialog,
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
      next: (res) => this.form.patchValue(res),
      error: (err) => this.handleError(err)
    });
  }

  getCredentials(): void {
    this.credentialService.getCredentials().subscribe({
      next: (res) => this.credentials = res,
      error: (err) => this.handleError(err)
    });
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }

  updateUser(): void {
    const user = this.form.value;

    this.userService.updateUser(user).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err)
    });
  }

}
