import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnginesComponent } from './engines.component';

describe('EnginesComponent', () => {
  let component: EnginesComponent;
  let fixture: ComponentFixture<EnginesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ EnginesComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EnginesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
