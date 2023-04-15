import { Component, Input, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { Credential } from '../credential';
import { CredentialService } from '../credential.service';
import { DialogService } from '../dialog.service';

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
    api_secret: '',
    api_password: '',
    active: false
  });

  @Input() credential?: Credential;

  constructor(
    private credentialService: CredentialService,
    private formBuilder: FormBuilder,
    private dialogService: DialogService
  ) {
  }

  ngOnInit(): void {
    if (this.credential?.api_key) {
      this.form.get('api_key')?.disable();
      this.form.get('api_secret')?.disable();
      this.form.get('api_password')?.disable();
      this.form.setValue({
        exchange: this.credential?.exchange,
        exchange_id: this.credential?.exchange_id,
        api_key: this.credential?.api_key.substring(0, 4) + '**************',
        api_secret: '*******************',
        api_password: '*******************',
        active: this.credential?.active
      });
    } else {
      this.form.setValue({
        exchange: this.credential?.exchange,
        exchange_id: this.credential?.exchange_id,
        api_key: '',
        api_secret: '',
        api_password: '',
        active: true
      });
    }
  }


  createForm(model: Credential): FormGroup {
    return this.formBuilder.group(model);
  }

  addCredential(): void {
    const cred = this.form.value;

    this.credentialService.addCredential(cred).subscribe({
      next: () => location.reload(),
    });
  }

  deleteCredential(): void {
    this.dialogService.confirm('Are you sure you want to delete this credential?').subscribe((res) => {
      if (res) {
        this.credentialService
          .deleteCredential(this.form.value.exchange_id)
          .subscribe({
            next: () => location.reload(),
          });
      }
    });
  }

  activateCredential(): void {
    const cred = this.form.value;
    cred.active = true;

    this.dialogService.confirm('Are you sure you want to reactivate this credential?').subscribe((res) => {
      if (res) {
        this.credentialService.updateCredential(cred).subscribe({
          next: () => location.reload(),
        });
      }
    });
  }

  deactivateCredential(): void {
    const cred = this.form.value;
    cred.active = false;

    this.dialogService.confirm('Are you sure you want to deactivate this credential?').subscribe((res) => {
      if (res) {
        this.credentialService.updateCredential(cred).subscribe({
          next: () => location.reload(),
        });
      }
    });
  }
}
