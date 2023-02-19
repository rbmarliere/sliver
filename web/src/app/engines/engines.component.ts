import { Component, OnInit } from '@angular/core';
import { Engine } from '../engine';
import { EngineService } from '../engine.service';
import { EnginesService } from '../engines.service';

@Component({
  selector: 'app-engines',
  templateUrl: './engines.component.html',
  styleUrls: ['./engines.component.less']
})
export class EnginesComponent implements OnInit {
  displayedColumns: string[] = [
    'id',
    'description',
    'actions',
  ];

  loading: Boolean = true;

  engines: Engine[] = [];

  constructor(
    private engineService: EngineService,
    private enginesService: EnginesService,
  ) { }

  ngOnInit(): void {
    this.getEngines();
  }

  getEngines(): void {
    this.loading = true;
    this.enginesService.getEngines().subscribe({
      next: (res) => {
        this.engines = res;
        this.loading = false;
      },
    });
  }

  deleteEngine(engine_id: number): void {
    this.engineService.deleteEngine(engine_id).subscribe({
      next: () => location.reload(),
    });
  }

}
