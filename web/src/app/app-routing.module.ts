import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from './auth.guard';
import { DashboardComponent } from './dashboard/dashboard.component';
import { EngineComponent } from './engine/engine.component';
import { EnginesComponent } from './engines/engines.component';
import { LoginGuard } from './login.guard';
import { LoginComponent } from './login/login.component';
import { OrderComponent } from './order/order.component';
import { PositionComponent } from './position/position.component';
import { PositionsComponent } from './positions/positions.component';
import { StrategiesComponent } from './strategies/strategies.component';
import { StrategyPerformanceComponent } from './strategy-performance/strategy-performance.component';
import { StrategyComponent } from './strategy/strategy.component';

const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
    canActivate: [LoginGuard]
  },
  {
    path: '',
    redirectTo: '/positions',
    pathMatch: 'full'
  },
  {
    path: 'order/:order_id',
    component: OrderComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'positions',
    component: PositionsComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'position/:position_id',
    component: PositionComponent,
    canActivate: [AuthGuard],
  },
  {
    path: 'strategies',
    component: StrategiesComponent,
    canActivate: [AuthGuard],
  },
  {
    path: 'strategy/:strategy_id',
    component: StrategyComponent,
    canActivate: [AuthGuard],
  },
  {
    path: 'strategy/:strategy_id/performance',
    component: StrategyPerformanceComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'engines',
    component: EnginesComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'engine/:engine_id',
    component: EngineComponent,
    canActivate: [AuthGuard]
  },
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [AuthGuard],
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule { }
