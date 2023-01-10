import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { Credential } from '../credential';
import { CredentialService } from '../credential.service';
import { Inventory } from '../inventory';
import { InventoryService } from '../inventory.service';
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

  displayedColumns: string[] = [
    'ticker',
    // 'free',
    // 'used',
    'total',
    // 'free_value',
    // 'used_value',
    'total_value',
  ];
  inventory: Inventory = {} as Inventory;

  loadingCred = true;
  credentials: Credential[] = [];

  constructor(
    private userService: UserService,
    private credentialService: CredentialService,
    private inventoryService: InventoryService,
    private formBuilder: FormBuilder
  ) { }

  ngOnInit(): void {
    this.getUser();
    this.getInventory();
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

  getInventory(): void {
    this.inventoryService.getInventory().subscribe({
      next: (res) => this.inventory = res
    });
  }

  getCredentials(): void {
    this.credentialService.getCredentials().subscribe({
      next: (res) => {
        this.credentials = res;
        this.loadingCred = false;
      }
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
