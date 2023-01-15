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
    max_risk: 0,
    cash_reserve: 0,
    telegram_username: '',
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

  loadingInv: Boolean = false;
  inventory: Inventory = {} as Inventory;

  loadingCred: Boolean = true;
  credentials: Credential[] = [];

  constructor(
    private userService: UserService,
    private credentialService: CredentialService,
    private inventoryService: InventoryService,
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

  getInventory(): void {
    this.loadingInv = true;
    this.inventoryService.getInventory().subscribe({
      next: (res) => {
        this.inventory = res
        this.loadingInv = false;
      }
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

  updatePassword(): void {
    const form = this.form.value;
    let user = {} as User;
    user.old_password = form.old_password;
    user.password = form.password;

    this.userService.updateUser(user).subscribe({
      next: () => location.reload()
    });
  }

  updateAlert(): void {
    const form = this.form.value;
    let user = {} as User;
    user.telegram_username = form.telegram_username;

    this.userService.updateUser(user).subscribe({
      next: () => location.reload()
    });
  }

  updateRisk(): void {
    const form = this.form.value;
    let user = {} as User;
    user.max_risk = form.max_risk;
    user.cash_reserve = form.cash_reserve;

    this.userService.updateUser(user).subscribe({
      next: () => location.reload()
    });
  }
}
