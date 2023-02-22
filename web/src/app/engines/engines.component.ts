import { Component, OnInit } from '@angular/core';
import { DialogService } from '../dialog.service';
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
    private dialogService: DialogService
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
    this.dialogService.confirm('Are you sure you want to delete this engine?').subscribe((res) => {
      if (res) {
        this.engineService.deleteEngine(engine_id).subscribe({
          next: () => location.reload(),
        });
      }
    });
  }

}
