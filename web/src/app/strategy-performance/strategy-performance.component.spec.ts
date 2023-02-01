import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StrategyPerformanceComponent } from './strategy-performance.component';

describe('StrategyPerformanceComponent', () => {
  let component: StrategyPerformanceComponent;
  let fixture: ComponentFixture<StrategyPerformanceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ StrategyPerformanceComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StrategyPerformanceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
