import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AuthGuard } from './auth.guard';
import { LoginGuard } from './login.guard';
import { LoginComponent } from './login/login.component';
import { PositionComponent } from './position/position.component';

const routes: Routes = [
      { path: 'login', component: LoginComponent, canActivate: [LoginGuard]},
      { path: '', redirectTo: '/positions', pathMatch: 'full' },
      { path: 'positions', component: PositionComponent, canActivate: [AuthGuard] },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
