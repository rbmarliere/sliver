import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Position } from '../position';
import { PositionService } from '../position.service';

@Component({
  selector: 'app-position',
  templateUrl: './position.component.html',
  styleUrls: ['./position.component.less']
})
export class PositionComponent implements OnInit {
  position: Position = {} as Position;
  loading: Boolean = true;

  constructor(
    private positionService: PositionService,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    const position_id = Number(this.route.snapshot.paramMap.get('position_id'));
    this.getPosition(position_id);
  }

  getPosition(position_id: number): void {
    this.positionService.getPosition(position_id).subscribe({
      next: (res) => {
        this.position = res;
        this.loading = false;
      }
    });
  }

}
