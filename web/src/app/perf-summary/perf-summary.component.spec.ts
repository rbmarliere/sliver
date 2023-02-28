import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PerfSummaryComponent } from './perf-summary.component';

describe('PerfSummaryComponent', () => {
  let component: PerfSummaryComponent;
  let fixture: ComponentFixture<PerfSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PerfSummaryComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PerfSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
