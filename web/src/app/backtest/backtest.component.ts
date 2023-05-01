import { formatDate } from '@angular/common';
import { Component, Input } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Engine } from '../engine';
import { IndicatorService } from '../indicator.service';
import { Strategy } from '../strategy';

@Component({
  selector: 'app-backtest',
  templateUrl: './backtest.component.html',
  styleUrls: ['./backtest.component.less']
})
export class BacktestComponent {
  loadingInd: Boolean = false;
  @Input() strategy!: Strategy;
  @Input() stopEngine!: Engine | null;
  form: FormGroup = this.createForm();

  createForm(): FormGroup {
    const now = new Date();
    const since = new Date(now.getFullYear(), 0, 1);

    return this.formBuilder.group({
      since: [formatDate(since, 'yyyy-MM-ddTHH:mm', 'en'), Validators.required],
      until: [formatDate(now, 'yyyy-MM-ddTHH:mm', 'en'), Validators.required],
    });
  }

  constructor(
    private formBuilder: FormBuilder,
    private indicatorService: IndicatorService,
  ) { }

  loadIndicators(): void {
    this.loadingInd = true;

    const since = this.form.value.since;
    const until = this.form.value.until;

    this.indicatorService.getIndicators(this.strategy.id, since, until).subscribe({
      next: (res) => {
        this.strategy.indicators = res;
        this.loadingInd = false;
      },
      error: () => {
        this.loadingInd = false;
        this.strategy.indicators = null;
      }
    });
  }

}

