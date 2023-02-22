import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSliderModule } from '@angular/material/slider';
import { MatTableModule } from '@angular/material/table';
import { MatToolbarModule } from '@angular/material/toolbar';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { PlotlyViaWindowModule } from 'angular-plotly.js';
import { RecaptchaV3Module, RECAPTCHA_V3_SITE_KEY } from 'ng-recaptcha';
import { environment } from 'src/environments/environment.prod';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AuthInterceptor } from './auth.interceptor';
import { CredentialComponent } from './credential/credential.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { EngineComponent } from './engine/engine.component';
import { EnginesComponent } from './engines/engines.component';
import { ErrorDialogComponent } from './error-dialog/error-dialog.component';
import { HttpErrorInterceptor } from './http-error.interceptor';
import { IndicatorComponent } from './indicator/indicator.component';
import { LoginComponent } from './login/login.component';
import { NavbarComponent } from './navbar/navbar.component';
import { OrderComponent } from './order/order.component';
import { PositionComponent } from './position/position.component';
import { StrategiesComponent } from './strategies/strategies.component';
import { StrategyPerformanceComponent } from './strategy-performance/strategy-performance.component';
import { StrategyComponent } from './strategy/strategy.component';

@NgModule({
  declarations: [
    AppComponent,
    CredentialComponent,
    DashboardComponent,
    ErrorDialogComponent,
    LoginComponent,
    NavbarComponent,
    OrderComponent,
    PositionComponent,
    StrategiesComponent,
    StrategyComponent,
    IndicatorComponent,
    StrategyPerformanceComponent,
    EngineComponent,
    EnginesComponent,
  ],
  imports: [
    AppRoutingModule,
    BrowserAnimationsModule,
    BrowserModule,
    HttpClientModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatGridListModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSliderModule,
    MatTableModule,
    MatToolbarModule,
    PlotlyViaWindowModule,
    ReactiveFormsModule,
    RecaptchaV3Module,
    MatListModule,
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
    {
      provide: HTTP_INTERCEPTORS,
      useClass: HttpErrorInterceptor,
      multi: true,
    },
    {
      provide: RECAPTCHA_V3_SITE_KEY,
      useValue: environment.recaptcha.siteKey,
    }
  ],
  bootstrap: [AppComponent],
})
export class AppModule { }
