import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';


import { AuthService } from '../auth.service';

@Component({
  selector: 'app-navbar',
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.less']
})
export class NavbarComponent implements OnInit {

  isMobile = false;
  menuIsOpen = false;
  isAuthenticated = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {
    this.isMobile = window.innerWidth < 768;
  }

  ngOnInit(): void {
    this.authService.authenticated.subscribe(value => this.isAuthenticated = value);
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/']);
  }

  toggleMenu() {
    this.menuIsOpen = !this.menuIsOpen;
  }

}
