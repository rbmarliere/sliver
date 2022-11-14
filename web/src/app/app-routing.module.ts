import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AuthGuard } from './auth.guard';
import { LoginGuard } from './login.guard';
import { LoginComponent } from './login/login.component';
import { PositionComponent } from './position/position.component';
import { StrategyComponent } from './strategy/strategy.component';

const routes: Routes = [
      { path: 'login', component: LoginComponent, canActivate: [LoginGuard]},
      { path: '', redirectTo: '/positions', pathMatch: 'full' },
      { path: 'positions', component: PositionComponent, canActivate: [AuthGuard] },
      { path: 'strategies', component: StrategyComponent, canActivate: [AuthGuard] },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
