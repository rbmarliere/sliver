import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Engine } from '../engine';
import { EngineService } from '../engine.service';
import { EnginesService } from '../engines.service';

@Component({
  selector: 'app-engine',
  templateUrl: './engine.component.html',
  styleUrls: ['./engine.component.less']
})
export class EngineComponent implements OnInit {
  private empty_engine = {
    id: 0,
    description: '',
    refresh_interval: 1,
    num_orders: 1,
    bucket_interval: 1,
    min_buckets: 1,
    spread: 0.01,
    stop_cooldown: 0,
    stop_gain: 0,
    trailing_gain: false,
    stop_loss: 0,
    trailing_loss: false,
    lm_ratio: 0,
  }

  engine: Engine = this.empty_engine;

  engine_id: number = 0;

  loading: Boolean = true;

  form = this.createForm(this.empty_engine);

  constructor(
    private engineService: EngineService,
    private enginesService: EnginesService,
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router
  ) { }

  ngOnInit(): void {
    const engine_id = Number(this.route.snapshot.paramMap.get('engine_id'));

    if (engine_id) {
      this.engine_id = engine_id;
      this.getEngine(engine_id);
    } else {
      this.loading = false;
      this.engine = this.empty_engine;
    }
  }

  createForm(model: Engine): FormGroup {
    return this.formBuilder.group(model);
  }

  getEngine(engine_id: number): void {
    this.loading = true;
    this.engineService.getEngine(engine_id).subscribe({
      next: (res) => {
        this.engine = res;
        this.form.patchValue(res);
        this.loading = false;
      }
    });
  }

  updateEngine() {
    const engine = this.form.getRawValue();

    if (this.engine_id > 0) {
      this.engineService.updateEngine(engine).subscribe({
        next: () => location.reload(),
      });
    } else {
      this.enginesService.createEngine(engine).subscribe({
        next: () => this.router.navigate(['/engines']),
      });
    }
  }

  formatLabel(value: number) {
    return Math.round(value * 100) + '%';
  }
}
