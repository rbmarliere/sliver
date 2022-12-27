import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StrategyDetailComponent } from './strategy-detail.component';

describe('StrategyDetailComponent', () => {
  let component: StrategyDetailComponent;
  let fixture: ComponentFixture<StrategyDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ StrategyDetailComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StrategyDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
