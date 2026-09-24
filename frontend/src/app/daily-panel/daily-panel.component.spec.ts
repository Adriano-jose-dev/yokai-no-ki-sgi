import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DailyPanelComponent } from './daily-panel.component';

describe('DailyPanelComponent', () => {
  let component: DailyPanelComponent;
  let fixture: ComponentFixture<DailyPanelComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DailyPanelComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DailyPanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
