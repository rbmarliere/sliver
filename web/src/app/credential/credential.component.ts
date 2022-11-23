import { HttpErrorResponse } from '@angular/common/http';
import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { Credential } from '../credential';
import { CredentialService } from '../credential.service';
import { ErrorDialogComponent } from '../error-dialog/error-dialog.component';

@Component({
  selector: 'app-credential',
  templateUrl: './credential.component.html',
  styleUrls: ['./credential.component.less']
})
export class CredentialComponent implements OnInit {

  form = this.createForm({
    exchange: '',
    exchange_id: 0,
    api_key: '',
    api_secret: ''
  });

  @Input() credential?: Credential;

  constructor(
    private credentialService: CredentialService,
    private dialog: MatDialog,
    private formBuilder: FormBuilder
  ) {
  }

  ngOnInit(): void {
    if (this.credential?.api_key) {
      this.form.get('api_key')?.disable()
      this.form.get('api_secret')?.disable()
      this.form.setValue({
        exchange: this.credential?.exchange,
        exchange_id: this.credential?.exchange_id,
        api_key: this.credential?.api_key,
        api_secret: '*******************'
      });
    } else {
      this.form.setValue({
        exchange: this.credential?.exchange,
        exchange_id: this.credential?.exchange_id,
        api_key: '',
        api_secret: ''
      });
    }
  }

  private handleError(error: HttpErrorResponse) {
    const dialogConfig = new MatDialogConfig

    dialogConfig.data = {
      msg: error.error.message
    };

    this.dialog.open(ErrorDialogComponent, dialogConfig);
  }

  createForm(model: Credential): FormGroup {
    return this.formBuilder.group(model);
  }

  addCredential(): void {
    const cred = this.form.value;

    this.credentialService.addCredential(cred).subscribe({
      next: () => location.reload(),
      error: (err) => this.handleError(err)
    });
  }

  deleteCredential(): void {
    this.credentialService
      .deleteCredential(this.form.value.exchange_id)
      .subscribe({
        next: () => location.reload(),
        error: (err) => this.handleError(err)
    });
  }

}
